// Rules sanity checks + a short AI self-play match.  Run: node test_rules.mjs
import * as R from '../game/js/rules.js';
import { chooseTurn } from '../game/js/ai.js';
const assert=(c,m)=>{if(!c){console.error('FAIL',m);process.exit(1)}};
assert(R.POINTS.length===37,'37 points');
const s=R.initialState();
assert(R.count(s,1)===16 && R.count(s,2)===16,'16 each');
// middle row empty
assert(R.POINTS.filter((p,i)=>p.z===0 && s.board[i]).length===0,'middle empty');
// adjacency sanity
const deg=R.ADJ.map(a=>a.length);
console.log('edges',R.EDGES.length,'deg center',deg[R.pointAt(0,0)],'corner',deg[R.pointAt(-2,-2)],'apex',deg[R.pointAt(0,-2)],'tri tip',deg[R.pointAt(0,-4)], 'tri corner', deg[R.pointAt(-2,-4)]);
assert(deg[R.pointAt(0,0)]===8,'center 8');
assert(deg[R.pointAt(1,0)]===4,'odd point 4');
// diag through apex into triangle
assert(R.ADJ[R.pointAt(0,-2)].includes(R.pointAt(-1,-3)),'apex->tri');
assert(R.ADJ[R.pointAt(1,-1)].includes(R.pointAt(0,-2)),'diag to apex');
assert(R.JUMPS[R.pointAt(1,-1)].some(j=>j.to===R.pointAt(-1,-3)),'jump through apex');
const a=R.legalActions(s); console.log('opening moves',a.length, a.map(x=>R.POINTS[x.from].x+','+R.POINTS[x.from].z+'>'+R.POINTS[x.to].x+','+R.POINTS[x.to].z).join(' '));
// self-play games
let res={1:0,2:0,0:0}, plies=0, t0=Date.now();
const GAMES=+(process.argv[2]||2);
for(let g=0;g<GAMES;g++){
  let st=R.initialState(); let o=null; let n=0;
  while(!(o=R.outcome(st)) && n<400){ const lvl = st.turn===1?(g%2===0?'hard':'easy'):(g%2===0?'easy':'hard'); const acts=chooseTurn(st,lvl); for(const x of acts) st=R.applyAction(st,x); n++; }
  res[o?o.winner:0]++; plies+=n; console.log('game',g,'P1',g%2===0?'hard':'easy','winner',o&&o.winner,o&&o.reason,'turns',n,'left',R.count(st,1),R.count(st,2));
}
console.log(res,'avg turns',plies/GAMES,'secs',(Date.now()-t0)/1000);
