"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const ns = "http://www.w3.org/2000/svg";
  const colors = {checked: "#95ddc2", related: "#f4ca84", question: "#c3b0f2", unchecked: "#71949f"};
  const centers = {"Pattern formation": [182, 169], "Selection and inheritance": [537, 169], "Molecular evolution": [182, 491], "Evolutionary games": [537, 491]};
  function svg(tag, attrs, parent) {
    const element = document.createElementNS(ns, tag);
    Object.entries(attrs).forEach(([k, v]) => element.setAttribute(k, v));
    parent.append(element); return element;
  }
  function words(text) {
    const parts = text.split(" ");
    if (text.length < 19 || parts.length === 1) return [text];
    let split = 1;
    for (let i = 1; i < parts.length; i++) if (Math.abs(parts.slice(0, i).join(" ").length - text.length / 2) < Math.abs(parts.slice(0, split).join(" ").length - text.length / 2)) split = i;
    return [parts.slice(0, split).join(" "), parts.slice(split).join(" ")];
  }
  function safeLink(url) {
    const parsed = new URL(url, location.href);
    if (parsed.protocol !== "https:" && !(parsed.origin === location.origin && ["http:", "file:"].includes(parsed.protocol))) throw new Error("Unsupported evidence URL");
    return parsed.href;
  }
  async function start() {
    const response = await fetch("frontier-data.json");
    if (!response.ok) throw new Error(`Inventory returned HTTP ${response.status}`);
    const data = await response.json(), positions = {}, map = $("map"), picker = $("claim-picker");
    if (data.nodes.length !== 21) throw new Error("Unexpected inventory size");
    const groups = Object.entries(centers);
    groups.forEach(([group, [cx, cy]]) => {
      svg("ellipse", {cx, cy, rx: 169, ry: 146, class: "region"}, map);
      const label = svg("text", {x: cx, y: cy - 135, "text-anchor": "middle", class: "group-label"}, map); label.textContent = group;
      const nodes = data.nodes.filter(n => n.group === group);
      nodes.forEach((node, i) => {
        const angle = -Math.PI / 2 + (i + .5) * 2 * Math.PI / nodes.length;
        positions[node.id] = [cx + 112 * Math.cos(angle), cy + 91 * Math.sin(angle)];
      });
    });
    data.bridges.forEach(edge => {
      const [x1,y1] = positions[edge.from], [x2,y2] = positions[edge.to];
      const line = svg("line", {x1,y1,x2,y2,class: `connection ${edge.kind}`, "data-from": edge.from,"data-to": edge.to}, map);
      svg("title", {}, line).textContent = edge.label;
    });
    data.nodes.forEach(node => {
      const [x,y] = positions[node.id];
      const g = svg("g", {class:"node", "data-id":node.id, role:"button",tabindex:0,"aria-label":`${node.short}: ${node.review_title}`,"aria-pressed":"false",transform:`translate(${x},${y})`}, map);
      svg("circle", {r:26,class:"hit"},g);
      svg("circle", {r:20,class:"halo"},g);
      svg("circle", {r:12,fill:colors[node.category],class:"node-core"},g);
      const label = svg("text", {"text-anchor":"middle", y:34},g);
      words(node.short).forEach((part,i) => {svg("tspan", {x:0,dy:i ? 15 : 0},label).textContent=part;});
      const activate = () => select(node.id);
      g.addEventListener("click",activate);
      g.addEventListener("keydown",event => {if (["Enter"," "].includes(event.key)) {event.preventDefault();activate();}});
      const option = document.createElement("option"); option.value = node.id; option.textContent = `${node.short} · ${node.review_title}`; picker.append(option);
    });
    function select(id) {
      const node = data.nodes.find(n => n.id === id); if (!node) return;
      picker.value=id; $("claim-panel").dataset.claimId=id;
      document.querySelectorAll(".node").forEach(g => {const active=g.dataset.id===id; g.classList.toggle("active",active);g.setAttribute("aria-pressed",String(active));});
      document.querySelectorAll(".connection").forEach(g => g.classList.toggle("active",[g.dataset.from,g.dataset.to].includes(id)));
      for(const [element,value] of Object.entries({"claim-group":node.group,"claim-title":node.label,"claim-status":node.review_title,"claim-statement":node.statement,"claim-finding":node.finding,"next-action":node.next_action,"claim-math":node.math,"claim-context":node.context,"claim-source":node.source,"claim-hash":node.record_sha256})) $(element).textContent=value;
      $("claim-status").className=`status-tag ${node.category}`;
      $("source-link").href=safeLink(node.source_url);
      $("evidence-links").replaceChildren();
      node.evidence.forEach(evidence => {const li=document.createElement("li"),a=document.createElement("a"); a.href=safeLink(evidence.url);a.textContent=evidence.label;li.append(a);$("evidence-links").append(li);});
      $("no-evidence").textContent=node.evidence.length ? "A linked artifact supports only its stated target and scope." : "No corresponding check is recorded in this inventory. Start with the extracted source below.";
      $("bridge-list").replaceChildren();
      const edges=data.bridges.filter(e=>e.from===id||e.to===id);
      edges.forEach(edge=>{const li=document.createElement("li");li.textContent=edge.label;$("bridge-list").append(li);});
      $("bridge-panel").hidden=!edges.length;
      $("evidence-panel").hidden=true; $("prove-button").setAttribute("aria-expanded","false");
    }
    picker.addEventListener("change",()=>select(picker.value));
    $("prove-button").addEventListener("click",()=>{const open=$("evidence-panel").hidden;$("evidence-panel").hidden=!open;$("prove-button").setAttribute("aria-expanded",String(open));});
    select("turing-ddi");
    const problemResponse = await fetch("frontier-problems.json");
    if (!problemResponse.ok) throw new Error("Problem inventory could not load");
    const problems = await problemResponse.json();
    problems.problems.forEach(problem => {
      const card=document.createElement("article");card.className="problem-card";card.dataset.problemId=problem.id;
      const tag=document.createElement("span");tag.className="eyebrow";tag.textContent=`${problem.id} / ${problem.state === "open" ? "Open in this project" : "Resolved in review"}`;
      const title=document.createElement("h3");title.textContent=problem.title;
      const question=document.createElement("p");question.textContent=problem.question;
      const details=document.createElement("details"),summary=document.createElement("summary");summary.textContent="What would count as progress?";details.append(summary);
      [["Known",problem.known],["Acceptance",problem.acceptance],["Next action",problem.next_action],["Reuse",problem.cache],["Dependencies",problem.depends_on.join(", ")||"None recorded"]].forEach(([label,text])=>{const p=document.createElement("p"),b=document.createElement("strong");b.textContent=label+": ";p.append(b,document.createTextNode(text));details.append(p);});
      const source=document.createElement("a");source.href=safeLink(problem.source);source.textContent="Inspect the existing evidence ↗";details.append(source);
      card.append(tag,title,question,details);
      if(problem.coordination_url){const join=document.createElement("a");join.href=safeLink(problem.coordination_url);join.textContent="Register interest / offer help ↗";join.className="join-link";card.append(join);}
      $("problem-cards").append(card);
    });
    $("load-status").textContent="";
  }
  start().catch(error=>{$("load-status").textContent=`The review inventory could not load: ${error.message}. Serve this static site over HTTP and try again.`;});
})();
