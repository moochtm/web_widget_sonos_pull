const wsUri = (window.location.protocol==='https:'&&'wss://'||'ws://')+window.location.host;
document.$WEB_SOCKET = new WebSocket(wsUri);

document.$WEB_SOCKET.addEventListener('open', () => {
     console.log('Connect');
 });

 document.$WEB_SOCKET.addEventListener('close', () => {
      console.log('Disconnect');
  });

 document.$WEB_SOCKET.addEventListener('message', (event) => {
    console.log(event);
    counter = 0;
    const NEW_DATA = JSON.parse(event.data);
    updateHTML("#widget", NEW_DATA.html);
});

function requestRefresh() {
    if (document.$WEB_SOCKET === null) {
        onNotConnected();
        return;
    }
    counter++;
    console.log(counter);
    if (counter > 1) {
        console.log("Server not responding!");
        updateHTML("#widget", "Server not responding!");
    }

    const toSend = {
        "action": "refresh",
        "sonos_name": "Kitchen"
    };
    document.$WEB_SOCKET.send(JSON.stringify(toSend));
    console.log("Refresh requested.");
}

function updateHTML(target, html){
    // const NEW_DATA = target;
    const rangeHTML = document.createRange().createContextualFragment(html);
    document.querySelector(target).innerHTML = '';
    document.querySelector(target).appendChild(rangeHTML);
}

function onNotConnected(){
    console.log("No connection established!");
}

var counter = 0;
setInterval(requestRefresh, 5000);