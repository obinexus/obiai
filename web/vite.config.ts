import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
import { viteStaticCopy } from 'vite-plugin-static-copy';

const backend = 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [
    react(),
    // Serve the MediaPipe Hands runtime (wasm, model files) locally instead
    // of from a CDN; VITE_MEDIAPIPE_BASE can point back to a CDN if needed.
    viteStaticCopy({
      targets: [
        {
          src: 'node_modules/@mediapipe/hands/*.{js,wasm,data,binarypb,tflite}',
          dest: 'mediapipe/hands',
        },
        {
          src: 'node_modules/@mediapipe/drawing_utils/drawing_utils.js',
          dest: 'mediapipe/drawing_utils',
        },
      ],
    }),
  ],
  server: {
    port: 5173,
    host: true, // bind 0.0.0.0 so other devices on the LAN can reach this
    proxy: {
      '/health': backend,
      '/version': backend,
      '/sessions': backend,
      '/ontology': backend,
      '/reason': backend,
      '/ws': { target: 'ws://127.0.0.1:8000', ws: true },
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
});
