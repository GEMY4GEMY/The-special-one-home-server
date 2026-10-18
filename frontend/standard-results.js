"use strict";
document.addEventListener("DOMContentLoaded",()=>{
  const admin=document.getElementById("admin-area");if(!admin)return;
  const panel=document.createElement("section");panel.className="panel admin-panel";
  panel.innerHTML='<h3>Student Results / نتائج الطلاب</h3><p class="muted">Teacher exams and custom practice; administrator access only.</p><button class="outline" type="button" id="std-results-refresh">Refresh results</button><p id="std-results-summary" role="status"></p><div id="std-results-list" class="results"></div>';
  admin.prepend(panel);
  const summary=panel.querySelector("#std-results-summary"),list=panel.querySelector("#std-results-list");
  async function refresh(){
    try{
      const response=await fetch("/api/admin/standard/results",{credentials:"same-origin"});
      const data=await response.json();
      if(!response.ok)throw Error(data.detail||"Cannot load results");
      summary.textContent="Total completed attempts: "+data.total+" (latest 500 shown)";
      list.replaceChildren();
      if(!data.results.length){list.textContent="No results yet.";return}
      for(const item of data.results){
        const row=document.createElement("div");row.className="result-item";
        const label=document.createElement("span");
        label.textContent=item.full_name+" | "+item.grade+" | "+item.exam_title+" ("+item.exam_type+")";
        const score=document.createElement("strong");
        score.textContent=item.score+" / "+item.maximum;
        row.append(label,score);list.append(row)
      }
    }catch(e){summary.textContent=e.message}
  }
  panel.querySelector("#std-results-refresh").onclick=refresh;
  document.addEventListener("tso:admin-login",refresh);
  if(!admin.classList.contains("hidden"))queueMicrotask(refresh);
});
