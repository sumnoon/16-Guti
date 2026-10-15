import { chooseTurn } from './ai.js';
self.onmessage = (e) => {
  const { id, state, level } = e.data;
  state.board = Int8Array.from(state.board);
  self.postMessage({ id, actions: chooseTurn(state, level) });
};
