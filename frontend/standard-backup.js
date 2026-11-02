"use strict";
document.addEventListener("DOMContentLoaded",()=>{
  const download=document.getElementById("tso-backup-download");
  const restore=document.getElementById("tso-restore-submit");
  const file=document.getElementById("tso-restore-file");
  const status=document.getElementById("tso-backup-status");
  if(!download||!restore||!file||!status)return;
  download.onclick=async()=>{
    download.disabled=true;status.textContent="Preparing backup / جار تجهيز النسخة...";
    try{
      const response=await fetch("/api/admin/standard/backup",{credentials:"same-origin"});
      if(!response.ok)throw new Error("Backup failed ("+response.status+")");
      const blob=await response.blob();
      const url=URL.createObjectURL(blob);
      const link=document.createElement("a");link.href=url;
      link.download="THE_SPECIAL_ONE_BACKUP_"+new Date().toISOString().slice(0,10)+".sqlite3";
      document.body.append(link);link.click();link.remove();
      setTimeout(()=>URL.revokeObjectURL(url),30000);
      status.textContent="Backup ready / تم تجهيز النسخة الاحتياطية";
    }catch(error){status.textContent=error.message}
    finally{download.disabled=false}
  };
  restore.onclick=async()=>{
    const selected=file.files?.[0];
    if(!selected){status.textContent="Choose a backup file first / اختر ملف النسخة أولاً";return}
    if(selected.size>50*1024*1024){status.textContent="Maximum file size is 50 MB";return}
    if(!confirm("WARNING: This will REPLACE all current accounts, questions and results with the backup. Continue? / تحذير: سيتم استبدال كل الحسابات والأسئلة والنتائج الحالية. هل أنت متأكد؟"))return;
    const phrase=prompt("Type RESTORE to confirm / اكتب RESTORE للتأكيد");
    if(phrase!=="RESTORE"){status.textContent="Restore cancelled / تم إلغاء الاستعادة";return}
    restore.disabled=true;status.textContent="Restoring database / جار استعادة البيانات...";
    try{
      const body=new FormData();body.append("file",selected);
      const response=await fetch("/api/admin/standard/restore",{method:"POST",body,credentials:"same-origin"});
      const result=await response.json();
      if(!response.ok)throw new Error(result.detail||"Restore failed ("+response.status+")");
      status.textContent="Restore completed. Sign in again. / تمت الاستعادة. سجل الدخول مرة أخرى.";
      alert("Database restored. Please sign in again / تمت الاستعادة. يرجى تسجيل الدخول من جديد.");
      location.reload();
    }catch(error){status.textContent=error.message}
    finally{restore.disabled=false}
  };
});
