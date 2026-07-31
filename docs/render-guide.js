const {chromium}=require('playwright');
(async()=>{
  const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome'});
  const p=await b.newPage();
  await p.goto('file://'+process.cwd()+'/docs/ghl-guide.html', {waitUntil:'load'});
  await p.pdf({
    path:'docs/Big-Rich-Hauling-GHL-Setup-Guide.pdf',
    format:'Letter', printBackground:true,
    margin:{top:'16mm',bottom:'18mm',left:'14mm',right:'14mm'},
    displayHeaderFooter:true,
    headerTemplate:'<div></div>',
    footerTemplate:'<div style="width:100%;font-family:Helvetica,Arial,sans-serif;font-size:7.5pt;color:#8A949E;padding:0 14mm;display:flex;justify-content:space-between;"><span>Big Rich Hauling — Website Estimator → GoHighLevel setup</span><span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>'
  });
  await b.close();
})();
