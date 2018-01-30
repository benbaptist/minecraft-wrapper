// Hooray, I just hit 111 commits on Wrapper.py's development branch. 
// Why am I saying this here? Because easter eggs.


function doArgs(passedargs){
    var args = "";
    args = "key=" + localStorage.sessionKey
	for(i in passedargs){
		args += "&" + i + "=" + encodeURIComponent(passedargs[i]);
		if(i == undefined) continue;
	}
	// console.log("ARGS:" + args);
	return args
}

var requests = {}

requests.action = function(action, arglist){
	var args = doArgs(arglist)

	var xmlhttp;
	xmlhttp = new XMLHttpRequest();
	xmlhttp.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      return JSON.parse(this.responseText)
        }
    };
    // console.log("GET /action/"+action+"?"+args)
	xmlhttp.open("GET", "/action/"+action+"?"+args, false);
	xmlhttp.overrideMimeType("application/json");
	xmlhttp.send(null);
	pay = JSON.parse(xmlhttp.responseText)["payload"];
	// console.log("PAY: "+pay);
    return pay;
}

requests.adminThreaded = function(action, arglist, callBack){
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
	pay = JSON.parse(xmlhttp.responseText)["payload"];
	// console.log("Callback PAY: "+pay);
    callBack(pay);
}
