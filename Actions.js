const ACTIONS = {
  // Existing code collaboration actions
  JOIN: "join",
  JOINED: "joined",
  DISCONNECTED: "disconnected",
  CODE_CHANGE: "code-change",
  SYNC_CODE: "sync-code",
  LEAVE: "leave",
  
  // Document collaboration actions
  DOC_JOIN: "doc-join",
  DOC_JOINED: "doc-joined",
  DOC_LEAVE: "doc-leave",
  DOC_CHANGE: "doc-change",
  DOC_RECEIVE_CHANGES: "doc-receive-changes",
  DOC_CURSOR_MOVE: "doc-cursor-move",
  DOC_CURSOR_UPDATE: "doc-cursor-update",
  DOC_CURSOR_REMOVED: "doc-cursor-removed",
  DOC_SAVE: "doc-save",
  DOC_LOAD: "doc-load",
  DOC_INIT: "doc-init",
  DOC_SYNC_REQUEST: "doc-sync-request",
  DOC_SYNC_COMPLETE: "doc-sync-complete",
  
  // Presence and user actions
  USER_PRESENCE: "user-presence",
  USER_JOINED: "user-joined",
  USER_LEFT: "user-left",
  USER_LIST: "user-list",
  
  // Existing voice chat actions
  VOICE_JOIN: "voice-join",
  VOICE_LEAVE: "voice-leave",
  VOICE_OFFER: "voice-offer",
  VOICE_ANSWER: "voice-answer",
  ICE_CANDIDATE: "ice-candidate",
  VOICE_PARTICIPANTS: "voice-participants",
  VOICE_USER_JOINED: "voice-user-joined",
  VOICE_USER_LEFT: "voice-user-left"
};

module.exports = ACTIONS;