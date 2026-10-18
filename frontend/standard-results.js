"use strict";
document.addEventListener("DOMContentLoaded",()=>{
  const admin=document.getElementById("admin-area");if(!admin)return;
  const panel=document.createElement("section");panel.className="panel admin-panel";
  panel.innerHTML='<h3>Student Results / نتائج الطلاب</h3><p class="muted">Teacher exams and custom practice; administrator access only.</p><input id="std-results-grade" placeholder="Filter by grade"><button class="outline" type="button" id="std-results-refresh">Refresh results</button><button class="outline" type="button" id="std-results-export">Export CSV / تصدير</button><button class="outline" type="button" id="std-results-xlsx">Excel (.xlsx)</button><button class="outline" type="button" id="std-results-pdf">PDF</button><button class="primary" type="button" id="std-results-print">Print / طباعة</button><p id="std-results-summary" role="status"></p><div id="std-results-list" class="results"></div>';
  admin.prepend(panel);
  const summary=panel.querySelector("#std-results-summary"),list=panel.querySelector("#std-results-list");
  let latest=[];
  async function refresh(){
    try{
      const grade=panel.querySelector("#std-results-grade").value.trim();
      const url="/api/admin/standard/results"+(grade?"?grade="+encodeURIComponent(grade):"");
      const response=await fetch(url,{credentials:"same-origin"});
      const data=await response.json();
      if(!response.ok)throw Error(data.detail||"Cannot load results");
      latest=data.results;
      summary.textContent="Students: "+data.students+" | Teacher exams: "+data.teacher_attempts+" | Custom practice: "+data.practice_attempts+" | Total: "+data.total+" (latest 500 shown)";
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
  panel.querySelector("#std-results-grade").addEventListener("change",refresh);
  panel.querySelector("#std-results-export").onclick=()=>{
    if(!latest.length){summary.textContent="No results to export.";return}
    const columns=["full_name","username","grade","exam_title","exam_type","score","maximum","submitted_at"];
    const escape=value=>{const raw=String(value??"");const safe=/^[=+@\-\t\r]/.test(raw)?"\u0027"+raw:raw;return '"'+safe.replaceAll('"','""')+'"'};
    const csv="\uFEFF"+[columns.join(","),...latest.map(item=>columns.map(key=>escape(item[key])).join(","))].join("\r\n");
    const url=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));
    const link=document.createElement("a");link.href=url;link.download="THE_SPECIAL_ONE_Student_Results.csv";link.click();URL.revokeObjectURL(url);
  };
  const reportUrl=path=>{const grade=panel.querySelector("#std-results-grade").value.trim();return path+(grade?"?grade="+encodeURIComponent(grade):"")};
  async function downloadReport(path,filename){
    const response=await fetch(reportUrl(path),{credentials:"same-origin"});
    if(!response.ok){summary.textContent="Report download failed: "+response.status;return}
    const blob=await response.blob();const url=URL.createObjectURL(blob);
    const link=document.createElement("a");link.href=url;link.download=filename;document.body.append(link);link.click();link.remove();
    setTimeout(()=>URL.revokeObjectURL(url),30000);
  }
  panel.querySelector("#std-results-xlsx").onclick=()=>downloadReport("/api/admin/standard/export.xlsx","THE_SPECIAL_ONE_Results.xlsx");
  panel.querySelector("#std-results-pdf").onclick=()=>downloadReport("/api/admin/standard/export.pdf","THE_SPECIAL_ONE_Results.pdf");
  panel.querySelector("#std-results-print").onclick=()=>window.open(reportUrl("/api/admin/standard/print"),"_blank","noopener");
  document.addEventListener("tso:admin-login",refresh);
  if(!admin.classList.contains("hidden"))queueMicrotask(refresh);
});
