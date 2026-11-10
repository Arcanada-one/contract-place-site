// Google Analytics 4 for contract.place.
//
// The Google tag is requested from Google's servers only after the reader has
// explicitly accepted analytics. The stored choice lives in localStorage under
// 'cookie-consent' and takes the values 'accepted' or 'functional'. Without a
// choice the banner is shown and no request leaves the browser.
'use strict';
function createAnalytics(target){
  const MEASUREMENT_ID='G-C5J1NVE11Z';
  const STORAGE_KEY='cookie-consent';
  const ACCEPTED='accepted';
  const NECESSARY='functional';
  const TAG_ORIGIN='https://www.googletagmanager.com/gtag/js?id=';
  const TEXT={
    en:{title:'Analytics and cookies',body:'We use Google Analytics 4 to measure how the published documents are read. Nothing is sent to Google before you accept. Your choice stays in this browser.',accept:'Accept analytics',necessary:'Necessary only',settings:'Cookie settings',close:'Close'},
    ru:{title:'Аналитика и cookie',body:'Мы используем Google Analytics 4, чтобы измерить, как читают опубликованные документы. До вашего согласия ничего не отправляется в Google. Ваш выбор остаётся в этом браузере.',accept:'Принять аналитику',necessary:'Только необходимые',settings:'Настройки cookie',close:'Закрыть'},
    'zh-Hans':{title:'分析与 Cookie',body:'我们使用 Google Analytics 4 衡量已发布文档的阅读情况。在您同意之前，不会向 Google 发送任何数据。您的选择仅保存在此浏览器中。',accept:'接受分析',necessary:'仅必要项',settings:'Cookie 设置',close:'关闭'}
  };
  function storedChoice(){
    try{
      const value=target.localStorage.getItem(STORAGE_KEY);
      return (value===ACCEPTED||value===NECESSARY)?value:null;
    }catch(error){return null}
  }
  function storeChoice(value){
    if(value!==ACCEPTED&&value!==NECESSARY)return null;
    try{target.localStorage.setItem(STORAGE_KEY,value)}catch(error){}
    return value;
  }
  function shouldLoadTag(choice){return choice===ACCEPTED}
  function consentDefaults(){
    return {analytics_storage:'granted',ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied'};
  }
  function tagSrc(){return TAG_ORIGIN+MEASUREMENT_ID}
  function currentText(){
    const root=target.document&&target.document.documentElement;
    const lang=(root&&root.lang)||'en';
    if(lang.indexOf('zh')===0)return TEXT['zh-Hans'];
    return TEXT[lang]||TEXT.en;
  }
  let banner=null;
  let bannerNodes=null;
  let tagStarted=false;
  function removeBanner(){
    if(banner&&banner.parentNode)banner.parentNode.removeChild(banner);
    banner=null;
    bannerNodes=null;
  }
  function showBanner(){
    removeBanner();
    const text=currentText();
    const doc=target.document;
    const box=doc.createElement('div');
    box.className='consent-banner';
    box.setAttribute('role','dialog');
    box.setAttribute('aria-labelledby','consent-banner-title');
    const inner=doc.createElement('div');
    inner.className='consent-banner-inner';
    const title=doc.createElement('h2');
    title.className='consent-banner-title';
    title.id='consent-banner-title';
    title.textContent=text.title;
    const body=doc.createElement('p');
    body.className='consent-banner-text';
    body.textContent=text.body;
    const actions=doc.createElement('div');
    actions.className='consent-banner-actions';
    const accept=doc.createElement('button');
    accept.type='button';
    accept.className='button';
    accept.setAttribute('data-consent',ACCEPTED);
    accept.textContent=text.accept;
    const necessary=doc.createElement('button');
    necessary.type='button';
    necessary.className='button button-quiet';
    necessary.setAttribute('data-consent',NECESSARY);
    necessary.textContent=text.necessary;
    actions.appendChild(accept);
    actions.appendChild(necessary);
    inner.appendChild(title);
    inner.appendChild(body);
    inner.appendChild(actions);
    box.appendChild(inner);
    doc.body.appendChild(box);
    banner=box;
    bannerNodes={title,body,accept,necessary};
  }
  // The interface language can change while the banner is open; the text follows it.
  function refreshBanner(){
    if(!bannerNodes)return;
    const text=currentText();
    bannerNodes.title.textContent=text.title;
    bannerNodes.body.textContent=text.body;
    bannerNodes.accept.textContent=text.accept;
    bannerNodes.necessary.textContent=text.necessary;
  }
  function startTag(){
    if(tagStarted)return;
    tagStarted=true;
    target.dataLayer=target.dataLayer||[];
    function gtag(){target.dataLayer.push(arguments)}
    target.gtag=gtag;
    gtag('consent','default',consentDefaults());
    gtag('js',new Date());
    gtag('config',MEASUREMENT_ID,{ads_data_redaction:true,allow_google_signals:false});
    const tag=target.document.createElement('script');
    tag.async=true;
    tag.src=tagSrc();
    target.document.head.appendChild(tag);
  }
  function pageView(){
    if(!tagStarted||!target.gtag)return;
    target.gtag('event','page_view',{page_location:target.location.href,page_title:target.document.title});
  }
  function applyChoice(choice){
    storeChoice(choice);
    removeBanner();
    if(shouldLoadTag(choice))startTag();
  }
  function install(){
    const choice=storedChoice();
    if(shouldLoadTag(choice))startTag();
    else if(choice===null)showBanner();
    target.document.addEventListener('click',(event)=>{
      const origin=event.target;
      if(!origin||!origin.closest)return;
      const pick=origin.closest('[data-consent]');
      if(pick){applyChoice(pick.getAttribute('data-consent'));return}
      if(origin.closest('[data-consent-settings]'))showBanner();
    });
  }
  return {install,storedChoice,storeChoice,shouldLoadTag,consentDefaults,tagSrc,currentText,pageView,refreshBanner,
    MEASUREMENT_ID,STORAGE_KEY,ACCEPTED,NECESSARY};
}
if(typeof module!=='undefined'&&module.exports){module.exports=createAnalytics}
else{
  const analytics=createAnalytics(window);
  window.CpAnalytics=analytics;
  analytics.install();
}
