// ===================================================================
//  Assistant mural - logique front (portrait, style DAKboard)
// ===================================================================
const $  = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

let sleepCfg = { idle_seconds:180, night_start:"23:00", night_end:"06:00", hdmi_power_off:true };
let lastActivity = Date.now();
let screensaverOn = false, nightOn = false;
let lastEvents = [];
let _ver = null;

// -------------------- Navigation --------------------
$$(".nav-btn").forEach(b => b.addEventListener("click", () => {
  $$(".nav-btn").forEach(x => x.classList.remove("active"));
  $$(".page").forEach(x => x.classList.remove("active"));
  b.classList.add("active");
  $("#page-" + b.dataset.page).classList.add("active");
}));

// -------------------- Icones meteo (SVG) --------------------
const ICO = {
  sun:`<svg viewBox="0 0 64 64" fill="none" stroke="#ffcf4d" stroke-width="3" stroke-linecap="round">
    <circle cx="32" cy="32" r="12" fill="#ffcf4d" stroke="none"/>
    <g><line x1="32" y1="6" x2="32" y2="14"/><line x1="32" y1="50" x2="32" y2="58"/>
    <line x1="6" y1="32" x2="14" y2="32"/><line x1="50" y1="32" x2="58" y2="32"/>
    <line x1="13" y1="13" x2="19" y2="19"/><line x1="45" y1="45" x2="51" y2="51"/>
    <line x1="51" y1="13" x2="45" y2="19"/><line x1="19" y1="45" x2="13" y2="51"/></g></svg>`,
  part:`<svg viewBox="0 0 64 64" fill="none" stroke="#ffcf4d" stroke-width="3" stroke-linecap="round">
    <circle cx="23" cy="22" r="9" fill="#ffcf4d" stroke="none"/>
    <g><line x1="23" y1="4" x2="23" y2="10"/><line x1="5" y1="22" x2="11" y2="22"/>
    <line x1="10" y1="9" x2="14" y2="13"/><line x1="36" y1="9" x2="32" y2="13"/></g>
    <path d="M24 44h22a9 9 0 0 0 0-18 12 12 0 0 0-23 3 8 8 0 0 0 1 15Z" fill="#c9d4e3" stroke="#c9d4e3"/></svg>`,
  cloud:`<svg viewBox="0 0 64 64" fill="none">
    <path d="M20 46h24a10 10 0 0 0 0-20 13 13 0 0 0-25 3 9 9 0 0 0 1 17Z" fill="#aab6c8" stroke="#aab6c8"/></svg>`,
  rain:`<svg viewBox="0 0 64 64" fill="none" stroke-linecap="round">
    <path d="M20 40h24a10 10 0 0 0 0-20 13 13 0 0 0-25 3 9 9 0 0 0 1 17Z" fill="#9fb0c6" stroke="#9fb0c6"/>
    <g stroke="#4cc2ff" stroke-width="3"><line x1="23" y1="48" x2="20" y2="56"/>
    <line x1="33" y1="48" x2="30" y2="56"/><line x1="43" y1="48" x2="40" y2="56"/></g></svg>`,
  snow:`<svg viewBox="0 0 64 64" fill="none" stroke-linecap="round">
    <path d="M20 40h24a10 10 0 0 0 0-20 13 13 0 0 0-25 3 9 9 0 0 0 1 17Z" fill="#c2cedd" stroke="#c2cedd"/>
    <g stroke="#e8f3ff" stroke-width="3"><line x1="24" y1="50" x2="24" y2="56"/>
    <line x1="34" y1="50" x2="34" y2="56"/><line x1="44" y1="50" x2="44" y2="56"/></g></svg>`,
  fog:`<svg viewBox="0 0 64 64" fill="none" stroke="#aab6c8" stroke-width="3" stroke-linecap="round">
    <line x1="12" y1="26" x2="52" y2="26"/><line x1="8" y1="34" x2="48" y2="34"/>
    <line x1="14" y1="42" x2="54" y2="42"/><line x1="10" y1="50" x2="44" y2="50"/></svg>`,
  storm:`<svg viewBox="0 0 64 64" fill="none" stroke-linecap="round">
    <path d="M20 38h24a10 10 0 0 0 0-20 13 13 0 0 0-25 3 9 9 0 0 0 1 17Z" fill="#8c9bb3" stroke="#8c9bb3"/>
    <path d="M32 40l-7 11h7l-3 9 11-14h-7l3-6Z" fill="#ffcf4d" stroke="none"/></svg>`
};
function wIcon(code){
  const c = +code;
  if(c===0) return ICO.sun;
  if(c===1) return ICO.part;
  if(c===2) return ICO.part;
  if(c===3) return ICO.cloud;
  if(c===45||c===48) return ICO.fog;
  if((c>=51&&c<=67)||(c>=80&&c<=82)) return ICO.rain;
  if((c>=71&&c<=77)||c===85||c===86) return ICO.snow;
  if(c>=95) return ICO.storm;
  return ICO.cloud;
}
function wShort(code){
  const c=+code;
  if(c===0) return "Soleil";
  if(c===1) return "Éclaircies";
  if(c===2) return "Nuageux";
  if(c===3) return "Couvert";
  if(c===45||c===48) return "Brouillard";
  if(c>=51&&c<=57) return "Bruine";
  if((c>=61&&c<=67)||(c>=80&&c<=82)) return "Pluie";
  if((c>=71&&c<=77)||c===85||c===86) return "Neige";
  if(c>=95) return "Orage";
  return "Nuageux";
}

// -------------------- Horloge --------------------
const JOURS = ["dimanche","lundi","mardi","mercredi","jeudi","vendredi","samedi"];
const MOIS  = ["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"];
function tick(){
  const d=new Date();
  const hh=String(d.getHours()).padStart(2,"0"), mm=String(d.getMinutes()).padStart(2,"0");
  $("#clock").textContent=`${hh}:${mm}`;
  $("#date").textContent=`${JOURS[d.getDay()]} ${d.getDate()} ${MOIS[d.getMonth()]}`;
  $("#ss-time").textContent=`${hh}:${mm}`;
  $("#ss-date").textContent=`${JOURS[d.getDay()]} ${d.getDate()} ${MOIS[d.getMonth()]}`;
  checkSleep();
}

// -------------------- Veille / nuit --------------------
function hm(s){ const [h,m]=s.split(":").map(Number); return h*60+m; }
function inNight(){
  const d=new Date(), now=d.getHours()*60+d.getMinutes();
  const a=hm(sleepCfg.night_start||"23:00"), b=hm(sleepCfg.night_end||"06:00");
  return a<b ? (now>=a&&now<b) : (now>=a||now<b);
}
function setDisplay(on){ fetch("/api/display/"+(on?"on":"off"),{method:"POST"}).catch(()=>{}); }
function checkSleep(){
  const idleMs=(sleepCfg.idle_seconds||180)*1000, night=inNight();
  if(night && !nightOn){ nightOn=true; $("#night").classList.remove("hidden"); if(sleepCfg.hdmi_power_off) setDisplay(false); }
  if(!night && nightOn){ nightOn=false; $("#night").classList.add("hidden"); setDisplay(true); }
  if(night) return;
  const idle=Date.now()-lastActivity>idleMs;
  if(idle && !screensaverOn){ screensaverOn=true; $("#screensaver").classList.remove("hidden"); }
  if(!idle && screensaverOn){ screensaverOn=false; $("#screensaver").classList.add("hidden"); }
}
function wake(){
  lastActivity=Date.now();
  if(screensaverOn){ screensaverOn=false; $("#screensaver").classList.add("hidden"); }
  if(nightOn){ nightOn=false; $("#night").classList.add("hidden"); setDisplay(true);
    clearTimeout(window._nt); window._nt=setTimeout(()=>{ if(inNight()){ nightOn=true; $("#night").classList.remove("hidden"); if(sleepCfg.hdmi_power_off) setDisplay(false);} },30000);
  }
}
["touchstart","mousedown","keydown"].forEach(ev=>document.addEventListener(ev,wake,{passive:true}));

// -------------------- Meteo --------------------
function renderWeather(w){
  if(!w||w.error) return;
  $("#w-icon").innerHTML=wIcon(w.code);
  $("#w-temp").textContent=w.temp; $("#w-temp").classList.remove("skeleton");
  $("#w-desc").textContent=w.desc; $("#w-place").textContent=w.name;
  $("#w-feels").textContent=w.feels; $("#w-wind").textContent=w.wind; $("#w-hum").textContent=w.hum;
  const c=$("#w-days"); c.innerHTML="";
  (w.days||[]).forEach(d=>{
    const el=document.createElement("div"); el.className="fc-day";
    el.innerHTML=`<div class="d">${d.label}</div><div class="i">${wIcon(d.code!=null?d.code:0)}</div>
      <div class="c">${wShort(d.code!=null?d.code:0)}</div>
      <div class="t"><b>${d.tmax}°</b> <span class="lo">${d.tmin}°</span></div>
      <div class="r">${d.rain!=null?d.rain+"%":""}</div>`;
    c.appendChild(el);
  });
}
function renderSensor(s){
  $("#s-temp").classList.remove("skeleton");
  if(s&&s.ok){ $("#s-temp").textContent=s.temp; $("#s-hum").textContent=s.hum; $("#s-state").textContent=""; }
  else { $("#s-temp").textContent="--"; $("#s-hum").textContent="--"; $("#s-state").textContent="capteur non détecté"; }
}

// -------------------- Calendrier du mois --------------------
function eventDaysOfMonth(events, year, month){
  // renvoie un Set des jours (1..31) du mois affiche qui ont >=1 evenement
  const set=new Map();
  (events||[]).forEach(e=>{
    const d=new Date(e.start);
    if(d.getFullYear()===year && d.getMonth()===month){
      const day=d.getDate(); set.set(day,(set.get(day)||0)+1);
    }
  });
  return set;
}
let viewY=null, viewM=null, selDay=null;
function eventsOfDay(events,y,m,d){
  return (events||[]).filter(e=>{const dd=new Date(e.start);return dd.getFullYear()===y&&dd.getMonth()===m&&dd.getDate()===d;});
}
function buildCalendar(events){
  const t=new Date();
  if(viewY===null){ viewY=t.getFullYear(); viewM=t.getMonth(); }
  const year=viewY, month=viewM;
  const isCur=(year===t.getFullYear()&&month===t.getMonth());
  $("#cal-month").textContent=`${MOIS[month]} ${year}`;
  const evMap=eventDaysOfMonth(events, year, month);
  const first=new Date(year,month,1);
  let startDow=(first.getDay()+6)%7;           // lundi=0
  const nbDays=new Date(year,month+1,0).getDate();
  const prevDays=new Date(year,month,0).getDate();
  const grid=$("#cal-grid"); grid.innerHTML="";
  const weeks=Math.ceil((startDow+nbDays)/7);
  const cells=weeks*7;
  for(let i=0;i<cells;i++){
    const cell=document.createElement("div"); cell.className="cal-cell";
    let dayNum, out=false;
    if(i<startDow){ dayNum=prevDays-startDow+1+i; out=true; }
    else if(i>=startDow+nbDays){ dayNum=i-startDow-nbDays+1; out=true; }
    else { dayNum=i-startDow+1; }
    if(out) cell.classList.add("out");
    if(!out && isCur && dayNum===t.getDate()) cell.classList.add("today");
    if(!out && selDay===dayNum) cell.classList.add("sel");
    let dots="";
    if(!out && evMap.has(dayNum)){
      const n=Math.min(evMap.get(dayNum),3);
      dots=`<div class="dots">${'<span class="dot"></span>'.repeat(n)}</div>`;
    } else { dots=`<div class="dots"></div>`; }
    cell.innerHTML=`<div class="num">${dayNum}</div>${dots}`;
    if(!out){ const dn=dayNum; cell.addEventListener("click",()=>{ selDay=dn; buildCalendar(lastEvents); showDayEvents(lastEvents); }); }
    grid.appendChild(cell);
  }
}
function showDayEvents(events){
  const title=$("#cal-day-title"), list=$("#cal-day-events");
  if(selDay==null){ title.textContent="Touche un jour pour voir les évènements"; list.innerHTML=""; return; }
  const evs=eventsOfDay(events,viewY,viewM,selDay).sort((a,b)=>a.start<b.start?-1:1);
  title.textContent=`${selDay} ${MOIS[viewM]} ${viewY}`;
  if(!evs.length){ list.innerHTML='<div class="cde-empty">Aucun évènement ce jour.</div>'; return; }
  list.innerHTML="";
  evs.forEach(e=>{
    const d=new Date(e.start);
    const when=e.allday?"Journée":d.toLocaleTimeString("fr-FR",{hour:"2-digit",minute:"2-digit"});
    const el=document.createElement("div"); el.className="cde";
    el.innerHTML=`<div class="cde-bar"></div><div class="cde-t"><div class="cde-1">${e.title}</div><div class="cde-2">${when}${e.location?" · "+e.location:""}</div></div>`;
    list.appendChild(el);
  });
}
// navigation calendrier
$("#cal-prev").addEventListener("click",()=>{ viewM--; if(viewM<0){viewM=11;viewY--;} selDay=null; buildCalendar(lastEvents); showDayEvents(lastEvents); });
$("#cal-next").addEventListener("click",()=>{ viewM++; if(viewM>11){viewM=0;viewY++;} selDay=null; buildCalendar(lastEvents); showDayEvents(lastEvents); });
$("#cal-today").addEventListener("click",()=>{ const t=new Date(); viewY=t.getFullYear(); viewM=t.getMonth(); selDay=t.getDate(); buildCalendar(lastEvents); showDayEvents(lastEvents); });

// -------------------- A venir (agenda) --------------------
function renderAgenda(cal){
  const list=$("#agenda-list"), empty=$("#agenda-empty");
  if(!cal||!cal.configured){ list.innerHTML=""; empty.classList.remove("hidden"); return; }
  empty.classList.add("hidden");
  const now=new Date();
  const up=(cal.events||[]).filter(e=>new Date(e.start)>=new Date(now.getTime()-2*3600*1000)).slice(0,6);
  if(!up.length){ list.innerHTML='<div class="agenda-empty">Aucun évènement à venir.</div>'; return; }
  list.innerHTML="";
  up.forEach(e=>{
    const d=new Date(e.start);
    const when = e.allday
      ? d.toLocaleDateString("fr-FR",{weekday:"short",day:"numeric",month:"short"})
      : d.toLocaleDateString("fr-FR",{weekday:"short",day:"numeric",month:"short"})+" · "+d.toLocaleTimeString("fr-FR",{hour:"2-digit",minute:"2-digit"});
    const el=document.createElement("div"); el.className="ev";
    el.innerHTML=`<div class="bar"></div><div class="et">
      <div class="e1">${e.title}</div><div class="e2">${when}${e.location?" · "+e.location:""}</div></div>`;
    list.appendChild(el);
  });
}

// -------------------- Bourse --------------------
function fmt(n,cur){ return (n>=0?"":"-")+Math.abs(n).toLocaleString("fr-FR",{minimumFractionDigits:2,maximumFractionDigits:2})+" "+(cur||"€"); }
function renderPortfolio(p){
  if(!p) return;
  const cur=p.currency==="EUR"?"€":(p.currency||"€");
  $("#pf-total").textContent=fmt(p.total_value,cur); $("#pf-total").classList.remove("skeleton");
  const pl=$("#pf-pl"); pl.textContent=(p.total_pl>=0?"+":"")+fmt(p.total_pl,cur)+` (${p.total_pl_pct}%)`;
  pl.className="pf-pl "+(p.total_pl>=0?"up":"down");
  const list=$("#pf-list"); list.innerHTML="";
  (p.rows||[]).forEach(r=>{
    const el=document.createElement("div"); el.className="row";
    const cls=r.pl>=0?"up":"down";
    el.innerHTML=`<div class="main"><div class="t1">${r.name}</div>
        <div class="t2">${r.qty} × ${r.price} ${cur} · ${r.ticker}</div></div>
      <div style="text-align:right"><div class="big">${fmt(r.value,cur)}</div>
        <div class="${cls}" style="font-size:2.5vw">${r.pl>=0?"+":""}${fmt(r.pl,cur)} (${r.pl_pct}%)</div></div>`;
    list.appendChild(el);
  });
  if(p.cash){
    const el=document.createElement("div"); el.className="row";
    el.innerHTML=`<div class="main"><div class="t1">Espèces</div></div>
      <div style="text-align:right"><div class="big">${fmt(p.cash,cur)}</div></div>`;
    list.appendChild(el);
  }
}

// -------------------- Trajets --------------------
function renderTravel(t){
  const list=$("#tr-list"), empty=$("#tr-empty");
  if(!t||!t.configured||!t.rows||!t.rows.length){ list.innerHTML=""; empty.classList.remove("hidden"); return; }
  empty.classList.add("hidden"); list.innerHTML="";
  t.rows.forEach(r=>{
    const el=document.createElement("div"); el.className="row";
    const traffic=r.delay>0?` · <span class="down">+${r.delay} min trafic</span>`:(r.minutes!=null?` · <span class="up">fluide</span>`:"");
    const val=r.minutes!=null?`<div class="big">${r.minutes} min</div><div class="t2">${r.km} km${traffic}</div>`:`<div class="t2">indispo</div>`;
    el.innerHTML=`<div class="main"><div class="t1">${r.name}</div></div><div style="text-align:right">${val}</div>`;
    list.appendChild(el);
  });
}

// -------------------- Musique (lecture en cours) --------------------
function renderNowPlaying(np){
  const art=$("#np-art"), title=$("#np-title"), artist=$("#np-artist"), dev=$("#np-dev");
  const note=`<svg viewBox="0 0 24 24" class="np-note"><circle cx="7" cy="18" r="2.6"/><circle cx="18" cy="16" r="2.6"/><path d="M9.6 18V6l10.4-2v12"/></svg>`;
  if(np && np.playing){
    if(np.art){ art.innerHTML=`<img src="${np.art}" alt="">`; }
    else { art.innerHTML=note; }
    title.textContent=np.title||"Lecture";
    artist.textContent=np.artist||"";
    dev.textContent=(np.source?np.source+" · ":"")+(np.device||"");
  } else {
    art.innerHTML=note;
    title.textContent="Rien en lecture";
    artist.textContent="";
    dev.textContent="";
  }
}
async function pollMusic(){
  try{ const r=await fetch("/api/nowplaying"); renderNowPlaying(await r.json()); }
  catch(e){}
}
// boutons de controle musique
$$("#np-ctrl .mbtn").forEach(b=>b.addEventListener("click",async()=>{
  try{ await fetch("/api/music/"+b.dataset.act,{method:"POST"}); }catch(e){}
  setTimeout(pollMusic,600);   // rafraichit l'etat apres l'action
}));
// ---- Radios web ----
async function loadRadios(){
  try{
    const r=await fetch("/api/radio/list"); const d=await r.json();
    const g=$("#radio-grid"); if(!g) return; g.innerHTML="";
    (d.stations||[]).forEach((name,i)=>{
      const b=document.createElement("button"); b.className="rbtn"; b.textContent=name;
      b.addEventListener("click",async()=>{
        const st=$("#radio-state"); if(st) st.textContent="Lancement de "+name+"…";
        try{ const rr=await fetch("/api/radio/"+i,{method:"POST"}); const j=await rr.json();
          if(st) st.textContent=j.ok?("▶ "+name):("✗ "+(j.reason||"échec")); }
        catch(e){ if(st) st.textContent="✗ erreur"; }
        setTimeout(pollMusic,1500);
      });
      g.appendChild(b);
    });
  }catch(e){}
}
loadRadios();

// -------------------- Aspirateur --------------------
function renderVacuum(v){
  const bat=$("#vac-bat"), label=$("#vac-label"), state=$("#vac-state");
  if(!bat) return;
  if(v && v.ok){
    bat.textContent=(v.battery!=null?v.battery:"--");
    label.textContent=v.label||"";
    state.textContent="";
  } else {
    bat.textContent="--"; label.textContent="Hors ligne";
    state.textContent=(v&&v.reason)?v.reason:"aspirateur non configuré";
  }
}
async function pollVacuum(){
  try{ const r=await fetch("/api/vacuum"); renderVacuum(await r.json()); }catch(e){}
}
$$("#page-maison .vbtn").forEach(b=>b.addEventListener("click",async()=>{
  const st=$("#vac-state"); if(st) st.textContent="envoi…";
  try{ const r=await fetch("/api/vacuum/"+b.dataset.vac,{method:"POST"}); const j=await r.json();
       if(st) st.textContent=j.ok?"✓ commande envoyée":"✗ échec"; }catch(e){ if(st) st.textContent="✗ erreur"; }
  setTimeout(pollVacuum,1500);
}));

// -------------------- Boucle --------------------
async function refresh(){
  try{
    const r=await fetch("/api/all"); const d=await r.json();
    if(d.sleep) sleepCfg=Object.assign(sleepCfg,d.sleep);
    renderWeather(d.weather); renderSensor(d.sensor);
    lastEvents = (d.calendar&&d.calendar.events)?d.calendar.events:[];
    buildCalendar(lastEvents); renderAgenda(d.calendar);
    renderPortfolio(d.portfolio); renderDonut(d.portfolio); renderTravel(d.travel);
    renderNowPlaying(d.nowplaying); renderVacuum(d.vacuum);
    if(d.system) renderSystem(d.system);
    if(d.time){ const u=new Date(d.time); const el=$("#w-updated");
      if(el) el.textContent="Mis à jour "+u.toLocaleTimeString("fr-FR",{hour:"2-digit",minute:"2-digit"}); }
    // auto-rechargement de l'ecran quand une nouvelle version est deployee
    if(d.version){ if(_ver===null){ _ver=d.version; } else if(d.version!==_ver){ setTimeout(()=>location.reload(true),600); } }
  }catch(e){ console.log("refresh err",e); }
}

// ---- Bourse : camembert de repartition ----
const DONUT_COLORS=["#4cc2ff","#35d07f","#e9b64a","#ff5a6a","#b07bff","#5ad0c0","#ff9f4a","#7aa2ff","#ff7bd0","#9bd04a","#c0d04a"];
function renderDonut(p){
  const el=$("#pf-donut"); if(!el||!p||!p.rows) return;
  const parts=p.rows.map(r=>({name:r.name,val:r.value})).filter(x=>x.val>0);
  if(p.cash) parts.push({name:"Espèces",val:p.cash});
  const tot=parts.reduce((a,b)=>a+b.val,0)||1;
  const C=2*Math.PI*42; let off=0, seg="";
  parts.forEach((pt,i)=>{ const len=pt.val/tot*C;
    seg+=`<circle cx="60" cy="60" r="42" fill="none" stroke="${DONUT_COLORS[i%DONUT_COLORS.length]}" stroke-width="15" stroke-dasharray="${len.toFixed(2)} ${(C-len).toFixed(2)}" stroke-dashoffset="${(-off).toFixed(2)}" transform="rotate(-90 60 60)"/>`;
    off+=len; });
  el.innerHTML=`<svg viewBox="0 0 120 120">${seg}<text x="60" y="57" text-anchor="middle" class="dn-t">${p.rows.length}</text><text x="60" y="73" text-anchor="middle" class="dn-s">lignes</text></svg>`;
  const lg=$("#pf-legend"); if(lg) lg.innerHTML=parts.map((pt,i)=>`<div class="lg"><span class="lgc" style="background:${DONUT_COLORS[i%DONUT_COLORS.length]}"></span>${pt.name} <b>${Math.round(pt.val/tot*100)}%</b></div>`).join("");
}

// ---- Divers : etat systeme / actus / programme (données réelles branchées ensuite) ----
function renderSystem(s){
  const g=$("#sys-grid"); if(!g) return;
  s=s||{cpu_temp:48,cpu:12,ram:34,disk:28,uptime:"3 j 4 h",version:"v16",ip:"192.168.1.89"};
  const items=[["CPU",s.cpu_temp+"°"],["Proc.",s.cpu+"%"],["RAM",s.ram+"%"],["Disque",s.disk+"%"],["Uptime",s.uptime],["Version",s.version],["IP",s.ip]];
  g.innerHTML=items.map(it=>`<div class="sys-item"><div class="sv">${it[1]}</div><div class="sk">${it[0]}</div></div>`).join("");
  const u=$("#upd-state"); if(u && !u.dataset.busy) u.textContent="Version "+(s.version||"?")+" · à jour ✓";
}
function renderNews(list){
  const el=$("#news-list"); if(!el) return;
  list=list||[
    {t:"Vigilance jaune pluie-inondation sur les Bouches-du-Rhône",s:"Météo-France"},
    {t:"Aubagne : le marché de Noël ouvre le 6 décembre",s:"France 3 Provence"},
    {t:"A50 : trafic ralenti vers Marseille en fin de journée",s:"Infotrafic"}];
  el.innerHTML=list.map(n=>`<div class="news-item"><div class="ni-t">${n.t}</div><div class="ni-s">${n.s}</div></div>`).join("");
}
const PROG_MOCK={
 "Auriol":[{d:"Sam 1 nov",t:"Marché provençal",l:"Place de la mairie"},{d:"Dim 9 nov",t:"Loto des associations",l:"Salle des fêtes"}],
 "Roquevaire":[{d:"Ven 7 nov",t:"Concert à l'église",l:"Église St-Vincent"}],
 "Cassis":[{d:"Sam 8 nov",t:"Marché aux santons",l:"Le port"},{d:"Dim 16 nov",t:"Vide-grenier",l:"Esplanade"}],
 "La Ciotat":[{d:"Sam 15 nov",t:"Festival du court-métrage",l:"Eden Théâtre"}]
};
function renderProgramme(ville){
  const el=$("#prog-list"); if(!el) return;
  const evs=PROG_MOCK[ville]||[];
  el.innerHTML=evs.length?evs.map(e=>`<div class="prog-item"><div class="pg-d">${e.d}</div><div class="pg-t">${e.t}</div><div class="pg-l">${e.l}</div></div>`).join(""):'<div class="cde-empty">Pas d\'évènement.</div>';
}
$$("#prog-tabs .ptab").forEach(b=>b.addEventListener("click",()=>{ $$("#prog-tabs .ptab").forEach(x=>x.classList.remove("active")); b.classList.add("active"); renderProgramme(b.dataset.ville); }));
const _upd=$("#upd-btn"); if(_upd) _upd.addEventListener("click",async()=>{
  const s=$("#upd-state"); if(s) s.textContent="Mise à jour en cours… l'écran va se recharger si besoin";
  try{ await fetch("/api/update",{method:"POST"}); }catch(e){}
  if(s) setTimeout(()=>{ s.textContent="À jour ✓ (recharge auto si nouveau code)"; }, 8000);
});
renderSystem(); renderNews(); renderProgramme("Auriol");

tick(); setInterval(tick,1000);
buildCalendar([]);                 // calendrier visible tout de suite
refresh(); setInterval(refresh,60000);
pollMusic(); setInterval(pollMusic,10000);   // la musique change souvent
pollVacuum(); setInterval(pollVacuum,30000); // etat aspirateur
