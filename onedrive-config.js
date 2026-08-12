// OneDrive VOICEVOX configuration for the Listening Game.
// The Microsoft Application (client) ID can be saved from the Listening page itself,
// so this file intentionally contains no secret and may keep clientId blank.
window.ONEDRIVE_VOICEVOX_CONFIG = {
  clientId: "",
  authority: "https://login.microsoftonline.com/consumers",
  redirectUri: "https://kanuli.github.io/japanese-vocab-game/listening.html",
  scopes: ["Files.ReadWrite.AppFolder"],
  indexFile: "voicevox-index.json",
  audioDir: "voicevox"
};
