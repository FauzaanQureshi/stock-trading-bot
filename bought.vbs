dim speechobject
set speechobject=createobject("sapi.spvoice")
ipo = WScript.Arguments.Item(0)
set speechobject.voice = speechobject.GetVoices.Item(1)
speechobject.speak "BOUGHT "+ipo+" STOCKS!"