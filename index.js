const express = require("express");
const app = express();
const http = require("http");
const { Server } = require("socket.io");
const ACTIONS = require("./Actions");
const cors = require("cors");
const axios = require("axios");
const server = http.createServer(app);
require("dotenv").config();

const clientId = process.env.JDOODLE_CLIENT_ID;
const clientSecret = process.env.JDOODLE_CLIENT_SECRET;

// Store states
const documentStates = new Map();
const userSocketMap = {};
const roomUsers = new Map();
const documents = new Map();

const languageConfig = {
  python3: { versionIndex: "3" },
  java: { versionIndex: "3" },
  cpp: { versionIndex: "4" },
  nodejs: { versionIndex: "3" },
  c: { versionIndex: "4" },
  ruby: { versionIndex: "3" },
  go: { versionIndex: "3" },
  scala: { versionIndex: "3" },
  bash: { versionIndex: "3" },
  sql: { versionIndex: "3" },
  pascal: { versionIndex: "2" },
  csharp: { versionIndex: "3" },
  php: { versionIndex: "3" },
  swift: { versionIndex: "3" },
  rust: { versionIndex: "3" },
  r: { versionIndex: "3" },
};

// Enable CORS and JSON parsing
app.use(cors());
app.use(express.json());

const io = new Server(server, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"],
  },
});

// Helper functions
const getAllConnectedClients = (roomId) => {
  return Array.from(io.sockets.adapter.rooms.get(roomId) || []).map(
    (socketId) => ({
      socketId,
      username: userSocketMap[socketId],
    })
  );
};

const getConnectedUsers = (roomId) => {
  return Array.from(roomUsers.get(roomId) || new Set()).map(socketId => ({
    socketId,
    username: userSocketMap[socketId]
  }));
};

io.on("connection", (socket) => {
    console.log('Socket connected:', socket.id);

    socket.on("error", (error) => {
        console.error("Socket error:", error);
    });

    // Document collaboration events
    socket.on(ACTIONS.DOC_JOIN, ({ roomId, username }) => {
      userSocketMap[socket.id] = username;
      socket.join(roomId);
      
      // Get current document state
      let document = documentStates.get(roomId);
      if (!document) {
        document = { ops: [] };
        documentStates.set(roomId, document);
      }
      
      // Update room users
      const roomUserSet = roomUsers.get(roomId) || new Set();
      roomUserSet.add(socket.id);
      roomUsers.set(roomId, roomUserSet);
      
      // Notify all clients in the room
      const clients = getAllConnectedClients(roomId);
      socket.emit(ACTIONS.DOC_INIT, {
        document,
        clients
      });
      
      socket.to(roomId).emit(ACTIONS.DOC_JOINED, {
        socketId: socket.id,
        username,
        clients
      });
    });

    socket.on(ACTIONS.DOC_CHANGE, ({ delta, roomId }) => {
      let document = documentStates.get(roomId);
      if (!document) {
        document = { ops: [] };
        documentStates.set(roomId, document);
      }

      // Update document state
      if (document.ops) {
        document.ops = [...document.ops, ...delta.ops];
      } else {
        document.ops = delta.ops;
      }
      documentStates.set(roomId, document);

      // Broadcast changes
      socket.to(roomId).emit(ACTIONS.DOC_RECEIVE_CHANGES, delta);
    });

    socket.on(ACTIONS.DOC_CURSOR_MOVE, ({ range, roomId }) => {
      socket.to(roomId).emit(ACTIONS.DOC_CURSOR_UPDATE, {
        socketId: socket.id,
        username: userSocketMap[socket.id],
        range
      });
    });

    // Voice chat events
    socket.on(ACTIONS.VOICE_JOIN, ({ roomId, username }) => {
      const voiceRoomId = `voice-${roomId}`;
      socket.join(voiceRoomId);
      
      const room = io.sockets.adapter.rooms.get(voiceRoomId);
      const participants = Array.from(room || [])
        .filter(id => id !== socket.id)
        .map(id => ({
          id,
          name: userSocketMap[id] || 'Unknown User'
        }));
      
      socket.emit(ACTIONS.VOICE_PARTICIPANTS, participants);
      socket.to(voiceRoomId).emit(ACTIONS.VOICE_USER_JOINED, {
        userId: socket.id,
        username
      });
    });

    socket.on(ACTIONS.VOICE_LEAVE, ({ roomId }) => {
      const voiceRoomId = `voice-${roomId}`;
      socket.to(voiceRoomId).emit(ACTIONS.VOICE_USER_LEFT, {
        userId: socket.id,
        username: userSocketMap[socket.id]
      });
      socket.leave(voiceRoomId);
    });

    socket.on(ACTIONS.VOICE_OFFER, ({ offer, peerId }) => {
      socket.to(peerId).emit(ACTIONS.VOICE_OFFER, {
        offer,
        peerId: socket.id
      });
    });

    socket.on(ACTIONS.VOICE_ANSWER, ({ answer, peerId }) => {
      socket.to(peerId).emit(ACTIONS.VOICE_ANSWER, {
        answer,
        peerId: socket.id
      });
    });

    socket.on(ACTIONS.ICE_CANDIDATE, ({ candidate, peerId }) => {
      socket.to(peerId).emit(ACTIONS.ICE_CANDIDATE, {
        candidate,
        peerId: socket.id
      });
    });
    
    // Code collaboration events
    socket.on(ACTIONS.JOIN, ({ roomId, username }) => {
      userSocketMap[socket.id] = username;
      socket.join(roomId);
      const clients = getAllConnectedClients(roomId);
      clients.forEach(({ socketId }) => {
        io.to(socketId).emit(ACTIONS.JOINED, {
          clients,
          username,
          socketId: socket.id,
        });
      });
    });

    socket.on(ACTIONS.CODE_CHANGE, ({ roomId, code }) => {
      socket.in(roomId).emit(ACTIONS.CODE_CHANGE, { code });
    });

    socket.on(ACTIONS.SYNC_CODE, ({ socketId, code }) => {
      io.to(socketId).emit(ACTIONS.CODE_CHANGE, { code });
    });

    // Handle disconnection
    socket.on("disconnecting", () => {
      const rooms = [...socket.rooms];
      rooms.forEach((roomId) => {
        // Remove user from room users
        const roomUserSet = roomUsers.get(roomId);
        if (roomUserSet) {
          roomUserSet.delete(socket.id);
          if (roomUserSet.size === 0) {
            roomUsers.delete(roomId);
          } else {
            roomUsers.set(roomId, roomUserSet);
          }
        }

        // Notify other users
        socket.to(roomId).emit(ACTIONS.DOC_CURSOR_REMOVED, socket.id);
        socket.in(roomId).emit(ACTIONS.DISCONNECTED, {
          socketId: socket.id,
          username: userSocketMap[socket.id],
        });

        // Handle voice chat disconnection
        if (roomId.startsWith('voice-')) {
          io.to(roomId).emit(ACTIONS.VOICE_USER_LEFT, {
            userId: socket.id,
            username: userSocketMap[socket.id]
          });
        }
      });

      delete userSocketMap[socket.id];
      socket.leave();
    });
});

// Code compilation endpoint
app.post("/compile", async (req, res) => {
  const { code, language } = req.body;

  try {
    const response = await axios.post("https://api.jdoodle.com/v1/execute", {
      script: code,
      language: language,
      versionIndex: languageConfig[language].versionIndex,
      clientId: process.env.JDOODLE_CLIENT_ID,
      clientSecret: process.env.JDOODLE_CLIENT_SECRET,
    });

    res.json(response.data);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: "Failed to compile code" });
  }
});

const PORT = process.env.PORT || 5000;
server.listen(PORT, () => console.log(`Server is running on port ${PORT}`));