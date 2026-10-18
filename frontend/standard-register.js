"use strict";
document.addEventListener("DOMContentLoaded",()=>{
  const toggle=document.getElementById("open-register");
  const panel=document.getElementById("register-panel");
  const form=document.getElementById("register-form");
  const status=document.getElementById("register-status");
  if(!toggle||!panel||!form)return;
  toggle.addEventListener("click",()=>{
    const open=panel.classList.toggle("hidden")===false;
    toggle.setAttribute("aria-expanded",String(open));
    if(open)document.getElementById("reg-full-name").focus();
  });
  form.addEventListener("submit",async event=>{
    event.preventDefault();
    const button=form.querySelector('button[type="submit"]');
    button.disabled=true;
    status.textContent="Creating your account...";
    try{
      const values=Object.fromEntries(new FormData(form).entries());
      const response=await fetch("/api/standard/register",{
        method:"POST",credentials:"same-origin",
        headers:{"Content-Type":"application/json"},body:JSON.stringify(values)
      });
      const data=await response.json();
      if(!response.ok)throw Error(typeof data.detail==="string"?data.detail:"Registration failed");
      document.getElementById("username").value=values.username;
      document.getElementById("password").value=values.password;
      form.reset();
      panel.classList.add("hidden");
      toggle.setAttribute("aria-expanded","false");
      document.getElementById("login-error").textContent="";
      status.textContent="";
      document.getElementById("login-form").requestSubmit();
    }catch(error){status.textContent=error.message}
    finally{button.disabled=false}
  });
});
