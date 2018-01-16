// Hooray, I just hit 111 commits on Wrapper.py's development branch. 
// Why am I saying this here? Because easter eggs.


function doArgs(passedargs){
    var args = "";
    args = "key=" + localStorage.sessionKey
	for(i in passedargs){
		console.log("arg :" + i);
		args += "&" + i + "=" + encodeURIComponent(passedargs[i]);
		if(i == undefined) continue;
	}
	console.log("ARGS:" + args);
	return args
}

var requests = {}

requests.testing = function(action, arglist){
    console.log("RUNNING 'REQUESTS.ACTION'")
    var args = doArgs(arglist);
    var XMLrequest = new XMLHttpRequest();
    XMLrequest.onreadystatechange = function () {
        var DONE = this.DONE || 4;
        if (this.readyState === DONE){
            alert(this.readyState);
            alert(this.responseText)
            return JSON.parse(this.responseText)
        }
    };
    XMLrequest.open("GET", "/action/"+action+"?"+args, true);
	XMLrequest.overrideMimeType("application/json");
	XMLrequest.send(null);
}

requests.action = function(action, arglist){
	var args = doArgs(arglist)

	var xmlhttp;
	xmlhttp = new XMLHttpRequest();
	xmlhttp.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      return JSON.parse(this.responseText)
        }
    };
	xmlhttp.open("GET", "/action/"+action+"?"+args, false);
	xmlhttp.overrideMimeType("application/json");
	xmlhttp.send(null);
    console.log("<"+xmlhttp.responseText+">");
    return JSON.parse(xmlhttp.responseText)["payload"];
}

requests.admin = function(action, arglist){
	var args = doArgs(arglist)

	var xmlhttp;
	xmlhttp = new XMLHttpRequest();
	xmlhttp.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      console.log("ADMIN RETURNED FROM IF")
      return JSON.parse(this.responseText)
        }
    };
	xmlhttp.open("GET", "/action/"+action+"?"+args, false);
	xmlhttp.overrideMimeType("application/json");
	xmlhttp.send(null);
    console.log("<"+xmlhttp.responseText+">");
    console.log("ADMIN RETURNED FROM END")
    return JSON.parse(xmlhttp.responseText);
}

requests.adminThreaded = function(action, arglist, callBack){
	var args = doArgs(arglist)

	var xmlhttp;
	xmlhttp = new XMLHttpRequest();
	xmlhttp.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      callBack(response["payload"]);
      return JSON.parse(this.responseText);
        }
    };
    xmlhttp.open("GET", "/action/"+action+"?"+args, false);
	xmlhttp.overrideMimeType("application/json");
	xmlhttp.send(null);

}