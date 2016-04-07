// Hooray, I just hit 111 commits on Wrapper.py's development branch. 
// Why am I saying this here? Because easter eggs.
requests = {}
requests.action = function(action, arguments){
	args = ""
	for(i in arguments){
		console.log(i)
		args += "&" + i + "=" + encodeURIComponent(arguments[i])
		if(i == undefined) continue
	}
//	console.log("GET Regular Request: /action/"+action+"?"+args)
	var xml = new XMLHttpRequest()
	xml.open("GET", "/action/"+action+"?"+args, false)
	xml.send()
	return JSON.parse(xml.responseText)
}
requests.admin = function(action, arguments){
	args = "key=" + localStorage.sessionKey
	for(i in arguments){
		if(i == undefined) continue
		args += "&" + i + "=" + encodeURIComponent(arguments[i])
	}
//	console.log("GET Admin Request: /action/"+action+"?"+args)
	var xml = new XMLHttpRequest()
	xml.open("GET", "/action/"+action+"?"+args, false)
	try{xml.send()}catch(err){return false}
	var response = JSON.parse(xml.responseText)
	if (response["status"] == "error")
		return false
	return response["payload"]
}
requests.adminThreaded = function(action, arguments, callBack){
	args = "key=" + localStorage.sessionKey
	for(i in arguments){
		if(i == undefined) continue
		args += "&" + i + "=" + encodeURIComponent(arguments[i])
	}
	try{
		var xml = new XMLHttpRequest()
		xml.open("GET", "/action/"+action+"?"+args, true)
	}catch(err){return false}
	try{xml.send()}catch(err){return false}
	xml.onreadystatechange = function(){
		if(xml.readyState == 4){
			try{
				var response = JSON.parse(xml.responseText)
			}catch(err){
				callBack(false)
				return
			}
			callBack(response["payload"])
		}
	}
}