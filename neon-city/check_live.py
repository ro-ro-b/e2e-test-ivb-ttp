"""Check the published URL; this is not a physical-iPad test."""
import hashlib, json, os, re, traceback, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

URL='https://rawcdn.githack.com/ro-ro-b/e2e-test-ivb-ttp/3a16ec9e30afe8de737dc267aaf48dec7ee0f562/neon-city/index.html'
root=Path(__file__).resolve().parent
out=root/'verification'
out.mkdir(exist_ok=True)
report={'url':URL,'checks':[],'physical_ipad_tested':False}
def check(name,ok,detail=None):
    item={'name':name,'passed':bool(ok)}
    if detail is not None:item['detail']=detail
    report['checks'].append(item)
    print(json.dumps(item),flush=True)
def save():
    report['all_passed']=bool(report['checks']) and all(c['passed'] for c in report['checks'])
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
try:
    req=urllib.request.Request(URL,headers={'User-Agent':'NeonCity-Verification/1.0'})
    with urllib.request.urlopen(req,timeout=40) as response:
        data=response.read();mime=response.headers.get('Content-Type','')
        check('Published page is HTML',response.status==200 and 'text/html' in mime,{'status':response.status,'content_type':mime,'bytes':len(data)})
        check('Published game matches original exactly',hashlib.sha256(data).hexdigest()=='001db22e807891e80a607f8a8ff623cda7784c93288481c7b1920eadcec61288')
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader','--use-angle=swiftshader'])
        context=browser.new_context(viewport={'width':1180,'height':820},device_scale_factor=1,has_touch=True,is_mobile=True)
        page=context.new_page();errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(URL,wait_until='domcontentloaded',timeout=60000)
        page.wait_for_timeout(2000)
        report['initial_page_text']=page.locator('body').inner_text()[:5000]
        if not page.evaluate('Boolean(window.Courtside)'):
            candidates=page.get_by_role('button',name=re.compile('continue|proceed|confirm|open|understand',re.I))
            links=page.get_by_role('link',name=re.compile('continue|proceed|confirm|open|understand',re.I))
            if candidates.count():
                candidates.first.click();report['confirmation_clicked']='button'
            elif links.count():
                links.first.click();report['confirmation_clicked']='link'
        page.wait_for_function('window.Courtside && window.Courtside.status().screen === "menu"',timeout=45000)
        check('Hosted game opens at team selection',True)
        page.screenshot(path=str(out/'hosted-menu.png'))
        page.locator('#practice').click()
        page.wait_for_function('Courtside.status().screen === "playing" && Courtside.status().mode === "practice"')
        check('Play button starts practice',True)
        initial=page.evaluate('Courtside.status()')
        joy=page.locator('#joystick').bounding_box();shoot=page.locator('#shoot').bounding_box()
        j={'x':joy['x']+joy['width']*.75,'y':joy['y']+joy['height']*.5,'id':1}
        s={'x':shoot['x']+shoot['width']*.5,'y':shoot['y']+shoot['height']*.5,'id':2}
        cdp=context.new_cdp_session(page)
        cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[j]})
        page.wait_for_timeout(500)
        cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[j,s]})
        page.wait_for_timeout(750)
        cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[j]})
        page.wait_for_timeout(120)
        shot=page.evaluate('Courtside.status()')
        cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
        check('Joystick moves player',abs(initial['players'][0]['x']-shot['players'][0]['x'])+abs(initial['players'][0]['y']-shot['players'][0]['y'])>1)
        check('Touch release launches shot',shot['ball'] in ['shot','net'],shot['ball'])
        page.wait_for_timeout(1300)
        page.locator('#pause').click();check('Pause button works',page.evaluate('Courtside.status().screen')=='paused')
        page.locator('#resume').click();check('Resume button works',page.evaluate('Courtside.status().screen')=='playing')
        page.screenshot(path=str(out/'hosted-game.png'))
        check('No uncaught JavaScript errors',not errors,errors)
        check('No visible game error overlay',not page.locator('#error').is_visible())
        browser.close()
except Exception as exc:
    check('Verification completed',False,str(exc));report['traceback']=traceback.format_exc()
finally:
    save()
