import * as THREE from 'three';
import {CSS2DObject} from 'three/addons/renderers/CSS2DRenderer.js';

export const stageNames:Record<string,string>={entry:'Entry',bag:'Bag drop',security_wait:'Security line',
  screening:'Screening',coffee:'Coffee',restroom:'Restroom',walk:'Gate'};

function sign(text:string, className:string) {
  const chip=document.createElement('span');chip.className=className;chip.textContent=text;
  return new CSS2DObject(chip);
}
export function journeyMap(scene:THREE.Scene, gatePoint:(id:string)=>THREE.Vector3|undefined) {
  const layer=new THREE.Group(), path=new THREE.Group(), signs=new THREE.Group();
  scene.add(layer);layer.add(path,signs);
  const points:Record<string,THREE.Vector3>={entry:new THREE.Vector3(-7,.3,7),
    bag:new THREE.Vector3(-8,.3,4),security_wait:new THREE.Vector3(-13,.3,5),
    screening:new THREE.Vector3(-10,.3,0)};
  const lineMaterial=new THREE.LineBasicMaterial({color:0x75eced,depthTest:false});
  const amenities=new THREE.Group();layer.add(amenities);
  function building(key:string,colour:number) {
    const site=new THREE.Group();
    function box(w:number,h:number,d:number,y:number, shade:number,z=0) {
      const mesh=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),new THREE.MeshStandardMaterial({color:shade}));
      mesh.position.set(0,y,z);site.add(mesh);
    }
    box(3,1.6,2.4,.8,colour);
    if(key==='coffee'){box(3.8,.24,3,2.2,0xffcd80);box(.18,.65,.18,1.9,colour);}
    else {box(3.3,.2,2.7,1.7,0xbbdeea);box(.8,1.2,.12,.6,0x25485e,-1.25);}
    const label=sign(stageNames[key],'amenity-sign');label.position.y=2.8;site.add(label);
    amenities.add(site);return site;
  }
  const cafe=building('coffee',0xbd6b35), toilets=building('restroom',0x5989ac);
  function clear() {
    for(const obj of signs.children.slice()){signs.remove(obj);(obj as CSS2DObject).element.remove();}
    for(const obj of path.children.slice()){path.remove(obj);(obj as THREE.Line).geometry.dispose();}
    layer.visible=false;
  }
  function locate() {
    const pairs:[[string,THREE.Group,string,string],[string,THREE.Group,string,string]]=[
      ['coffee',cafe,'GATE_A1','GATE_A2'],['restroom',toilets,'GATE_A5','GATE_A6']];
    for(const [key,site,a,b] of pairs){
      const first=gatePoint(a),second=gatePoint(b);if(!first||!second)return false;
      site.position.copy(first).lerp(second,.5);site.position.y=0;
      points[key]=site.position.clone();points[key].z*=.68;points[key].y=.3;
    }
    layer.visible=true;return true;
  }
  function route(keys:string[],gate:string) {
    clear();if(!locate())return;
    const dest=gatePoint(gate);if(!dest)return;
    points.walk=dest.clone();points.walk.y=.3;points.walk.z*=.65;
    const ordered=['entry',...keys];
    const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(ordered.map(k=>points[k])),lineMaterial);
    line.renderOrder=5;path.add(line);
    ordered.forEach((key,i)=>{
      const label=sign(String(i+1),'route-number');label.element.title=stageNames[key];
      label.position.copy(points[key]);label.position.y=1.4;signs.add(label);
    });
  }
  function highlight(index:number) {
    signs.children.forEach((s,i)=>(s as CSS2DObject).element.classList.toggle('current',i===index));
  }
  return {points,clear,locate,route,highlight};
}
