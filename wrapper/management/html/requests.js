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

requests.action = function(action, arguments){

    var args = doArgs(arguments);
    var XMLrequest = new XMLHttpRequest();
    XMLrequest.onreadystatechange = function () {
        var DONE = this.DONE || 4;
        if (this.readyState === DONE){
            alert(this.readyState);
            return JSON.parse(this.responseText)
        }
    };

    XMLrequest.open("GET", "/action/"+action+"?"+args, false);
	XMLrequest.overrideMimeType("application/json");
	XMLrequest.send(null);

}

requests.action_orig = function(action, arguments){

    var args = doArgs(arguments)

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
}

requests.admin = function(action, arguments){
	var args = doArgs(arguments)

	var xmlhttp;
	xmlhttp = new XMLHttpRequest();
	xmlhttp.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      return JSON.parse(this.responseText)
        }
    };
	xmlhttp.open("GET", "/action/"+action+"?"+args, false);
	xmlhttp.overrideMimeType("application/json");
	// xmlhttp.responseType = 'json';
    xmlhttp.send(null);
    //while(xmlhttp.readyState != 4){
    //    console.log(xmlhttp.readyState)
    //    console.log("waiting");
    //}
    console.log("<"+xmlhttp.responseText+">");
    return JSON.parse(xmlhttp.responseText)["payload"];
}

requests.adminThreaded = function(action, arguments, callBack){
	var args = doArgs(arguments)

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