# Session Handoff — 2026-05-11

> 本檔由 Claude Code session 結束時寫入。新 session 啟動後可讀此檔恢復狀態，讀完可刪。

---

## ✅ 2026-05-11 最終更新：bug 是真的，已重新修好（commit `6e48ceb`）

**前一段「已全部回滾」的判斷錯了**，下面的「為什麼回滾」推論在做完真正的診斷後被推翻。為了避免後人讀到誤判，把正解寫在這裡：

### 實際結果
- 兩個 bug 都是真的，在主 repo `dc97e13` 上重現
- 一次 commit 修掉：`6e48ceb` "Fix stale marker and transcript server warning on Streamlit rerun"
- Worktree 是無辜的，跟這兩個 bug 沒關係

### 核心發現（值得記到 DEVLOG）
**Streamlit 的 `st.rerun(scope="app")` 會用新的 globals 重新執行整個 module body**，所以任何 module-level state（`_transcript_server_started = False`、`_last_persisted = {}`、`_stale_marker_cleaned`...）都會被重設。一般的「按按鈕觸發 rerun」不會這樣（main() 重跑、globals 保留），但 `st.rerun(scope="app")` 會。本 repo 的 `start_recording()` 結束時就會呼叫 `st.rerun(scope="app")`，每次按 Start Recording 都觸發 module 重執行。

### Bug 真正的 root cause
1. **Stale marker → auto-Viewer**：`stop_meeting_translator.command` 是 SIGTERM/SIGKILL 硬殺，不會走到 `_clear_active_session_marker()`。下次啟動讀到殘留 marker → 強制進 Viewer。**這在主 repo 正常使用就會踩到**，跟 worktree 完全無關。我先前判斷「主 repo 不會有這個 race」是錯的。
2. **Port 8580 warning**：第一次 bind 確實成功、server 一直 alive、warning 確實是 cosmetic，但**根因不是「Streamlit rerun 重執行 module body」這麼單純** ── 是 `st.rerun(scope="app")` 觸發的特殊 rerun 才會重設 globals，所以我先前提議的 `globals()` 哨兵 fix **無效**（哨兵自己也被新 globals 蓋掉）。

### 正確修法（已在 `6e48ceb`）
- **Bug 1**：marker 寫入帶 `os.getpid()`，`_cleanup_stale_marker_on_startup()` 在 main() 開頭跑（PID 已死才清、自己的不動），用 `sys._mt_stale_marker_checked` 做 process-level guard
- **Bug 2**：`_start_transcript_server` 改用 `sys._mt_transcript_server_started` ── `sys` 屬性是 process-level，不受 module 重執行影響
- 兩個 bug 共用同一個 pattern：**需要 process-level state 時用 `sys` 屬性，不要用 module 變數**

### 我之前 cd75526 沒抓到的 latent bug
cd75526 的 `_cleanup_stale_marker_on_startup` 在 `owner_pid == os.getpid()` 時會「保險起見清掉」── 但 `start_recording()` 之後馬上 `st.rerun(scope="app")`，cleanup 又跑一次、看到自己剛寫的 marker、把它砍了。`6e48ceb` 改成「自己的 marker 保留」，並且用 sys guard 讓 cleanup 整個 process 只跑一次。

### 保留的設定
- `~/.claude/settings.json` 的 worktree deny 規則仍然保留（這個跟 bug 無關，純粹防 Claude Code auto-spawn）

---

## ⚠️ 2026-05-11 後續更新：已全部回滾

> **以下這一整段是錯的判斷，留作為對照。實際結論看上面「最終更新」。**


下個 session 啟動後檢視發現：**本檔記錄的兩個 bug 其實都是 worktree 環境造成的偽問題，主 repo 正常使用根本不會踩到**。決議回滾到 `dc97e13` 重新來過。

### 回滾範圍
- **丟掉** commit `cd75526`（stale marker fix：marker 加 pid、`_cleanup_stale_marker_on_startup()`、`_pid_alive()`）
- **丟掉** commit `bb79a4f`（這是後續 session 中新加的 `_ReuseAddrHTTPServer` SO_REUSEADDR fix，從未 push）
- **丟掉** 未 commit 的 globals() 哨兵（為了消 Streamlit rerun 重複 bind warning 的 cosmetic 修改）
- 執行：`git reset --hard dc97e13`，HEAD 與 origin/main 同步（0 ahead）

### 為什麼回滾
1. **Bug 1（Live Viewer 自動進入）的真實 root cause**：上次 session 在 Claude Code auto-spawn 的 worktree 工作，worktree 跑 Streamlit 沒走 Stop → marker 殘留 → 下次主 repo 啟動誤判。**主 repo 正常使用（用 `run_meeting_translator.command` 起、`stop_meeting_translator.command` 停）不會有這個 race**。
2. **Bug 2（Errno 48 / port 8580）**：實際確認後是 Streamlit rerun 在**同一個 process** 內重呼叫 `_start_transcript_server()` 撞自己 port，第一次 bind 早已成功，server 一直在跑，console 那行 "啟動失敗" 是 cosmetic noise，功能完全沒壞。別台機器同樣會看到，只是沒注意。
3. 兩個「fix」都在處理 worktree 切換造成的環境異常，不是程式碼真實 defect。為避免引入沒驗證過的副作用（特別是 cd75526 動到 marker 寫入/啟動清理邏輯），決定整個拿掉，回到別台機器都正常運作的 `dc97e13`。

### 保留的設定（不在 repo 內，不受 reset 影響）
- `~/.claude/settings.json` 加的 `permissions.deny: ["EnterWorktree", "ExitWorktree"]` ── **保留**。這是防止 Claude Code 再自動 spawn worktree 的根本對策，跟程式碼 bug 無關。

### 後續若真的要修 cosmetic warning
若以後想消掉 Streamlit rerun 撞 port 那行 warning，最小改動是在 `_start_transcript_server()` 開頭加 `if "_transcript_server_started" not in globals():` 哨兵（讓 flag 跨 rerun 存活）。但這是純美觀，不修也沒事。

---

## 本次 session 做了什麼

### 1. Bug fix：Live Viewer 卡死無法回主畫面
- **症狀**：每次重啟 app 都直接跳進 Live Viewer，按返回鍵也會被擋
- **根因**：上次 Streamlit 沒走完 Stop 流程就被關掉，`transcripts/.active_session.json` 殘留；dc97e13 加的 auto-enter 邏輯把新 browser 連線當成「子裝置連到主電腦」，自動進 Viewer
- **修法**（commit `cd75526`，已合進 `main`）：
  - `_write_active_session_marker()` 寫入時帶 `os.getpid()`
  - 新增 `_cleanup_stale_marker_on_startup()`：行程啟動時讀 marker，用 `os.kill(pid, 0)` 探活，PID 已死才清；PID 還活著（另一個 Streamlit 在錄）就保留
  - 主 repo `app.py` 與 worktree 同步、stale marker 已刪
  - 147 個 pytest 全過

### 2. 環境清理
- Kill 掉 6 天前留下的 orphan Streamlit（PID 64118, port 9999, anaconda python）
- 移除 3 個 Claude 自動 spawn 的 worktree：
  - `lucid-shannon-d3c09a`（本次工作用，已合進 main）
  - `cool-montalcini`、`thirsty-pasteur`（2026-03-23~24 的廢棄探索分支，內容遠落後 main，work 都已在 main 重做）
- `.claude/worktrees/` 目錄已刪

### 3. 永久禁用 worktree 自動 spawn
- `~/.claude/settings.json` 加入：
  ```json
  "permissions": {
    "deny": ["EnterWorktree", "ExitWorktree"]
  }
  ```
- deny 規則優先於 `bypassPermissions`，下次起 Claude Code 不會再自動 spawn worktree

## 主 repo 目前狀態

- branch: `main`，HEAD `cd75526` Fix auto-enter Live Viewer triggering on stale marker
- 比 `origin/main` 多 2 個 commit 未 push（`cd75526` + 上一個 `dc97e13`）
- working tree 有**先前 session 留下的未 commit 改動**（**不是本次改的**），等你決定怎麼處理：
  - `CLAUDE.md`
  - `docs/dev/ARCHITECTURE.md`
  - `docs/dev/BACKLOG.md`
  - `docs/dev/CURRENT_SPRINT.md`
  - `docs/dev/DEVLOG.md`

## 下次 session 建議優先處理

1. **驗收 bug fix**：`streamlit run app.py` 確認新 session 不會再被踢進 Live Viewer
2. **處理上述未 commit 的 docs 改動**：看起來是某次 doc cleanup 工作做到一半留下的，內容是大量刪除（DEVLOG -99 行、BACKLOG -97 行）── 確認是否要保留、commit 或捨棄
3. 視需要 `git push` 把這次 bug fix 推上 origin
4. 本檔 `SESSION_HANDOFF_20260511.md` 任務完成後可刪

## 相關檔案

- `app.py:6-13` — 加入 `import os`
- `app.py:293-302` — `_write_active_session_marker` 加 `pid` 欄位
- `app.py:347-405` — 新增 `_pid_alive()` 和 `_cleanup_stale_marker_on_startup()`
- `app.py:1137-1138` — `main()` 呼叫 startup cleanup
- `~/.claude/settings.json` — worktree deny 規則
