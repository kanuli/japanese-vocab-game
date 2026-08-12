# VOICEVOX + OneDrive 設定指南

這個方案**不需要 Cloudflare、Vercel、Azure Function 或 Client Secret**。

架構：

`GitHub Pages → Microsoft 登入（PKCE）→ OneDrive App Folder → VOICEVOX MP3`

遊戲只要求 Microsoft Graph 的 `Files.ReadWrite.AppFolder` 權限，因此只可存取 OneDrive 內屬於本遊戲的專用 App Folder，不需要讀取整個 OneDrive。

## 1. 建立 Microsoft App Registration

1. 登入 Microsoft Entra admin center。
2. 進入 **Entra ID → App registrations → New registration**。
3. Name：`Japanese Listening Game`。
4. Supported account types：如果使用個人 Microsoft / OneDrive 帳戶，選 **Personal accounts only**。如果想同時支援公司／學校帳戶，選 **Any Entra ID Tenant + Personal Microsoft accounts**。
5. 按 **Register**。
6. 在 Overview 複製 **Application (client) ID**。

> Client ID 不是密碼，可以放在瀏覽器或公開網站。不要建立或貼上 Client Secret。

## 2. 設定 GitHub Pages Redirect URI

1. 在剛建立的 App Registration 打開 **Authentication**。
2. 選 **Add a platform → Single-page application**。
3. 加入：

`https://kanuli.github.io/japanese-vocab-game/listening.html`

4. 儲存。

## 3. 加入 OneDrive 權限

1. 打開 **API permissions → Add a permission**。
2. 選 **Microsoft Graph → Delegated permissions**。
3. 搜尋並勾選：`Files.ReadWrite.AppFolder`。
4. 按 **Add permissions**。

個人 Microsoft 帳戶不需要建立 Client Secret；登入時由使用者同意權限。

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

在同一部 iPhone 的 Safari 開啟遊戲並登入 Microsoft 後，MSAL 會在瀏覽器保存登入狀態／token cache。遊戲每次播放時會向 Microsoft Graph 取得當下有效的短期 OneDrive download URL，再播放 MP3。

因此：

- 不需要下載 Supertonic 約 400 MB 模型才能聽 VOICEVOX 錄音。
- 不需要每次下載整個音訊庫，只會串流目前題目的小型音訊檔。
- Microsoft 的短期 download URL 不會永久寫入 GitHub；遊戲需要時才重新取得。

## 7. 備援順序

選 VOICEVOX 時：

1. OneDrive 有該題 VOICEVOX 錄音 → 播放 VOICEVOX。
2. 找不到錄音但 Supertonic 已啟用 → 使用 Supertonic AI。
3. 兩者均不可用 → 使用裝置日語語音。

下一步是建立批次 VOICEVOX 音訊產生器，把 Hanabira 題目轉成符合上述檔名的 MP3 與 `voicevox-index.json`。
