type Box={x:number;y:number;width:number;height:number};
export function placeLabels(boxes:Box[],width:number,height:number):Box[]{
  const placed:Box[]=[];
  for(const b of boxes){
    const clamp=(v:number,max:number)=>Math.max(0,Math.min(max,v));
    const xs=[b.x,...placed.flatMap(p=>[p.x-b.width-3,p.x+p.width+3])];
    const ys=[b.y,...placed.flatMap(p=>[p.y-b.height-3,p.y+p.height+3])];
    let best={...b}, distance=Infinity;
    for(const rawX of xs)for(const rawY of ys){
      const x=clamp(rawX,width-b.width),y=clamp(rawY,height-b.height);
      const score=(b.x-x)**2+(b.y-y)**2;
      if(score>=distance || placed.some(p=>x<p.x+p.width+2 && x+b.width+2>p.x &&
        y<p.y+p.height+2 && y+b.height+2>p.y))continue;
      best={...b,x,y};distance=score;
    }
    placed.push(best);
  }
  return placed;
}

let last='';
export function layoutLabels(root:HTMLElement){
  // Reserve the projected block tops before placing amenity signs and route markers.
  const nodes=['.label','.amenity-sign','.route-number']
    .flatMap(selector=>Array.from(root.querySelectorAll<HTMLElement>(selector)))
    .filter(node=>node.style.display!=='none');
  const signature=[root.clientWidth,root.clientHeight,...nodes.map(n=>n.style.transform+n.textContent+n.offsetWidth+','+n.offsetHeight)].join('|');
  if(signature===last && nodes.every(n=>n.style.translate))return;
  last=signature;
  nodes.forEach(n=>n.style.translate='none');
  const bounds=root.getBoundingClientRect();
  const boxes=nodes.map(n=>{const r=n.getBoundingClientRect();return {x:r.x-bounds.x,y:r.y-bounds.y,width:r.width,height:r.height};});
  placeLabels(boxes,bounds.width,bounds.height).forEach((p,i)=>{
    nodes[i].style.translate=(p.x-boxes[i].x)+'px '+(p.y-boxes[i].y)+'px';
  });
}
