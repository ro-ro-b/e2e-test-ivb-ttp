"""Verify the actual public game URL and native touch input. Not a physical-iPad test."""
import hashlib,json,re,traceback,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
URL='https://rawcdn.githack.com/ro-ro-b/e2e-test-ivb-ttp/3a16ec9e30afe8de737dc267aaf48dec7ee0f562/neon-city/index.html'
out=Path(__file__).resolve().parent/'verification';out.mkdir(exist_ok=True)
report={'url':URL,'physical_ipad_tested':False,'checks':[]}
def check(name,ok,detail=None):
 c={'name':name,'passed':bool(ok),'detail':detail};report['checks'].append(c);print(json.dumps(c),flush=True)
try:
 with urllib.request.urlopen(URL,timeout=40) as r:
  data=r.read();check('Public HTML matches complete original game',r.status==200 and hashlib.sha256(data).hexdigest()=='001db22e807891e80a607f8a8ff623cda7784c93288481c7b1920eadcec61288')
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader','--use-angle=swiftshader'])
  context=browser.new_context(viewport={'width':1180,'height':820},device_scale_factor=1,has_touch=True,is_mobile=True)
  page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(URL,wait_until='domcontentloaded',timeout=60000);page.wait_for_timeout(2000)
  report['initial_page_text']=page.locator('body').inner_text()[:2500]
  if not page.evaluate('Boolean(window.Courtside)'):
   page.get_by_role('button',name=re.compile('open the page',re.I)).click()
  page.wait_for_function('window.Courtside && Courtside.status().screen==="menu"',timeout=45000)
  check('Hosted game starts at team menu',True);page.screenshot(path=str(out/'hosted-menu.png'))
  page.locator('#practice').click();page.wait_for_function('Courtside.status().screen==="playing"')
  check('Practice starts',page.evaluate('Courtside.status().mode')=='practice')
  page.evaluate("window.touchTrace=[];['pointerdown','pointerup','pointercancel','lostpointercapture'].forEach(type=>document.addEventListener(type,e=>touchTrace.push({type,id:e.pointerId,target:e.target.id,x:e.clientX,y:e.clientY}),true))")
  cdp=context.new_cdp_session(page)
  def point(selector,id,fx=.5):
   r=page.locator(selector).bounding_box();return {'x':r['x']+r['width']*fx,'y':r['y']+r['height']*.5,'id':id}
  def event(kind,points):cdp.send('Input.dispatchTouchEvent',{'type':kind,'touchPoints':points})
  before=page.evaluate('Courtside.status()');j=point('#joystick',1,.75)
  event('touchStart',[j]);page.wait_for_timeout(600);event('touchEnd',[])
  after=page.evaluate('Courtside.status()')
  check('Touch joystick moves player',abs(before['players'][0]['x']-after['players'][0]['x'])+abs(before['players'][0]['y']-after['players'][0]['y'])>1)
  s=point('#shoot',2);event('touchStart',[s]);page.wait_for_timeout(750);event('touchEnd',[]);page.wait_for_timeout(80)
  shot=page.evaluate('Courtside.status()');check('Hold and release touch fires shot',shot['ball'] in ['shot','net'],shot)
  page.wait_for_timeout(3500)
  j=point('#joystick',3,.7);s=point('#shoot',4)
  event('touchStart',[j,s]);page.wait_for_timeout(750);event('touchEnd',[]);page.wait_for_timeout(80)
  simultaneous=page.evaluate('Courtside.status()');check('Movement and shooting together',simultaneous['ball'] in ['shot','net'],simultaneous)
  page.wait_for_timeout(1700);page.locator('#pause').click();check('Pause works',page.evaluate('Courtside.status().screen')=='paused')
  page.locator('#resume').click();check('Resume works',page.evaluate('Courtside.status().screen')=='playing')
  check('No JavaScript errors',not errors,errors);check('No game error overlay',not page.locator('#error').is_visible())
  report['touch_trace']=page.evaluate('touchTrace');page.screenshot(path=str(out/'hosted-game.png'))
  browser.close()
except Exception as e:
 check('Browser verification completed',False,str(e));report['traceback']=traceback.format_exc()
finally:
 report['all_passed']=all(c['passed'] for c in report['checks']);(out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
