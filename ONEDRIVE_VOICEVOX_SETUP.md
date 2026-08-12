# VOICEVOX + OneDrive 設定指南

這個方案**不需要 Cloudflare、Vercel、Azure Function 或 Client Secret**。

架構：

`GitHub Pages → Microsoft 登入（PKCE）→ OneDrive App Folder → VOICEVOX MP3`

遊戲只要求 Microsoft Graph 的 `Files.ReadWrite.AppFolder` 權限，因此只可存取 OneDrive 內屬於本遊戲的專用 App Folder，不需要讀取整個 OneDrive。

## 0. 先確認你能使用 Microsoft App registrations

Microsoft 現時的 App Registration 文件列出 Azure account / active subscription 及 Microsoft Entra tenant 為前置條件。

1. 先登入 Microsoft Entra admin center。
2. 看看是否可以進入 **Entra ID → App registrations**。
3. 如果你已經看得到 **New registration**，直接做下一節。
4. 如果系統說你沒有 tenant／directory，先建立 Microsoft Entra tenant（可使用 Default Directory／開發用 tenant），再回來做下一節。

你的 1 TB OneDrive 仍然是實際儲存 VOICEVOX 音訊的位置；Entra App Registration 只用來讓這個 GitHub Pages 網頁安全地取得你的授權。

## 1. 建立 Microsoft App Registration

1. 登入 Microsoft Entra admin center。
2. 進入 **Entra ID → App registrations → New registration**。
3. Name：`Japanese Listening Game`。
4. Supported account types：如果使用個人 Microsoft / OneDrive 帳戶，選 **Personal accounts only**。如果想同時支援公司／學校帳戶，選 **Any Entra ID Tenant + Personal Microsoft accounts**。
5. 按 **Register**。
6. 在 Overview 複製 **Application (client) ID**。

> Client ID 不是密碼，可以放在瀏覽器或公開網站。這是 browser SPA／public client，因此不要建立或貼上 Client Secret。

## 2. 設定 GitHub Pages Redirect URI

1. 在剛建立的 App Registration 打開 **Authentication**。
2. 選 **Add a platform → Single-page application**。
3. 加入以下 Redirect URI（必須完全相同）：

`https://kanuli.github.io/japanese-vocab-game/listening.html`

4. 儲存。

## 3. 加入 OneDrive 權限

1. 打開 **API permissions → Add a permission**。
2. 選 **Microsoft Graph → Delegated permissions**。
3. 搜尋並勾選：`Files.ReadWrite.AppFolder`。
4. 按 **Add permissions**。

`Files.ReadWrite.AppFolder` 讓遊戲讀寫自己的 App Folder，而不是取得整個 OneDrive 的完整檔案權限。

## 4. 在遊戲內連接 OneDrive

1. 開啟 `https://kanuli.github.io/japanese-vocab-game/listening.html`。
2. 在「日語語音」選 `🎭 VOICEVOX / OneDrive`。
3. 將 **Application (client) ID** 貼入 Client ID 欄位。
4. 按 **儲存 Client ID**。頁面會重新載入。
5. 再選 `🎭 VOICEVOX / OneDrive`，按 **連接 OneDrive**。
6. 用存有 1 TB OneDrive 的 Microsoft 帳戶登入並允許 App Folder 權限。
7. 按 **建立 VOICEVOX 資料夾**。

Microsoft 會建立類似：

`OneDrive / Apps / Japanese Listening Game /`

本遊戲會在裡面建立：

- `voicevox/`
- `voicevox-index.json`

## 5. 音訊檔案命名規則

如果沒有特別的索引紀錄，遊戲會依序尋找：

- `voicevox/N5/N5-0-0.mp3`
- `voicevox/N5/N5-0-0.m4a`
- `voicevox/N5/N5-0-0.wav`

因此每個 Hanabira 題目可以直接以題目 ID 命名，不需要把臨時 OneDrive download URL 寫入 GitHub。

`voicevox-index.json` 可額外記錄角色／風格：

```json
{
  "version": 1,
  "items": {
    "N5-0-0": {
      "path": "voicevox/N5/N5-0-0.mp3",
      "speaker": "四国めたん",
      "style": "ノーマル",
      "credit": "VOICEVOX:四国めたん"
    }
  }
}
```

## 6. iPhone

在同一部 iPhone 的 Safari 開啟遊戲並登入 Microsoft 後，MSAL Browser 會管理登入／token cache。遊戲播放 VOICEVOX 時向 Microsoft Graph 取得當下有效的 OneDrive download URL，再播放該題的音訊檔。

因此：

- 不需要下載 Supertonic 約 400 MB 模型才能聽已生成的 VOICEVOX 錄音。
- 不需要每次下載整個音訊庫，只會串流目前題目的音訊檔。
- 短期 download URL 不會永久寫入 GitHub；需要時重新取得。
- 如果 Safari 清除了網站資料／登入狀態，可能需要重新登入 Microsoft，但 OneDrive 裡的音訊檔不會因此刪除。

## 7. 備援順序

選 VOICEVOX 時：

1. OneDrive 有該題 VOICEVOX 錄音 → 播放 VOICEVOX。
2. 找不到錄音但 Supertonic 已啟用 → 使用 Supertonic AI。
3. 兩者均不可用 → 使用裝置日語語音。

## 8. 用 GitHub Actions 產生 VOICEVOX 聲音包

Repo 已加入 **Generate VOICEVOX audio pack** workflow。它會啟動官方 VOICEVOX Engine、讀取 Hanabira 題目、產生 MP3、建立 `voicevox-index.json`，最後輸出 ZIP artifact。

1. 在 GitHub repo 打開 **Actions**。
2. 左邊選 **Generate VOICEVOX audio pack**。
3. 按 **Run workflow**。
4. 選 JLPT，例如 `N5`。
5. Count 先用 `20` 測試；確認成功後可改為更大的數字或 `ALL`。
6. Speaker name 例如 `四国めたん`。
7. Style name 例如 `ノーマル`；如果不填，generator 會使用該角色的第一個 style。
8. Run workflow。
9. 成功後，在該 workflow run 的 **Artifacts** 下載 ZIP。
10. 解壓 ZIP，把裡面的 `voicevox/` 資料夾及 `voicevox-index.json` 上傳到本遊戲的 OneDrive App Folder。

Generator 會把角色 credit 寫進 index，例如 `VOICEVOX:四国めたん`。使用其他角色／聲音庫前，仍需遵守該角色及 voice library 的個別使用條款。

## 9. 最終檢查

1. 回到 Listening Game。
2. 選 `🎭 VOICEVOX / OneDrive`。
3. 開始一局包含已生成題目的 JLPT 等級。
4. 按播放。如果 OneDrive 有該題 MP3，播放狀態會顯示 `VOICEVOX · 角色／風格`。
5. 回答後，結果面板的「語音」也會顯示本題實際使用的聲音來源。

如果該題尚未生成 VOICEVOX MP3，遊戲會依序使用 Supertonic（如已啟用）或裝置日語語音備援。
