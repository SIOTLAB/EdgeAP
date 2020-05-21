import swarm
import selectors
import socket
import threading
import json
import types

request_server_str = "request_server"
shutdown_server_str = "shutdown_server"

class Manager:

    def __init__(self, config_file):
        self.config_file = config_file
        self.swarm = swarm.DockerSwarm(config_file)
        self.sockets = {}
        self.threads = {}
        self.mutex = threading.Lock()

    def shutdown(self):
        # Shutdown all sockets
        for _, sock in self.sockets.items():
            sock.shutdown(socket.SHUT_WR)
        # Shutdown all threads
        self.stop_threads = True

    def accept_connection(self, sock, sel):
        conn, addr = sock.accept()  # Should be ready to read
        print("accepted connection from ", addr)
        conn.setblocking(False)
        data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
        #events = selectors.EVENT_READ | selectors.EVENT_WRITE
        events = selectors.EVENT_READ 
        sel.register(conn, events, data=data)
        
    def start_request_server(self):
        self.threads[request_server_str] = threading.Thread(target=self.request_server, daemon=True)
        self.threads[request_server_str].start()

    def request_server(self):
        HOST = ""
        PORT = 60001
        sel = selectors.DefaultSelector()

        # Create, bind, and listen on socket
        self.sockets[request_server_str] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sockets[request_server_str].bind((HOST, PORT))
        self.sockets[request_server_str].listen()
        print("listening on", (HOST, PORT))
        self.sockets[request_server_str].setblocking(False)

        # Select self.socks[request_server] for I/O event monitoring 
        sel.register(self.sockets[request_server_str], selectors.EVENT_READ, data=None)

        while True:
            # wait until selector is ready (or timeout expires)
            events = sel.select(timeout=None)

            # For each file object, process
            for key, mask in events:
                if key.data is None:
                    self.accept_connection(key.fileobj, sel)
                else:
                    self.mutex.acquire()
                    self.process_request(key, mask, sel)
                    self.mutex.release()

    def process_request(self, key, mask, sel):
        sock = key.fileobj
        data = key.data

        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(1024)
            if recv_data:
                # Receive and decode request
                print("Received" , repr(recv_data), "from", data.addr)
                raw_data = recv_data.decode()
                request = json.loads(raw_data)

                '''
                Request Format:
                {
                	"image": <image-name>,
			"application_port": <port-exposed-in-container>,
                	"protocol": <tcp-or-udp>
                }

                Response Format:
                {
                	"resp-code": <0 on success, -1 on failure>,
			"service_id": <service id of running application>
            		"ip": <ip of device running application>,
			"port": <port for communication>,
                	"failure-msg": <failure message>
                }
                '''
                response = {}
                # Check for invalid request
                if "image" not in request or \
                   "application_port" not in request or \
                   "protocol" not in request:
                    response["resp-code"] = -1
                    response["failure-msg"] = "Invalid request"
                    sock.sendall(json.dumps(response).encode())
                    return

                '''
                Create application on the appropriate access point
                
                NOTE:
                    This is currently a proof-of-concept implementation
                    so we are simply selecting the first node (AP) in the list. 
                    In the future need to add logic for managing multiple remote AP's
                    and for intelligent placement of the applications.
		    The list of AP's are to be listed in the config.

                For now just using the only "remote" node listed in the config
                '''
                ip = list(self.swarm.nodes.keys())[0] # grab first ip in list
                (resp, service_id) = self.swarm.create_service(ip, request)

                if resp is False:
                    response["resp-code"] = -1
                    response["failure-msg"] = "Failed to start application"
                    sock.sendall(json.dumps(response).encode())
                    return

                service_info = self.swarm.get_service_info(service_id)
                port = service_info["Spec"]["EndpointSpec"]["Ports"][0]["PublishedPort"]
                response["resp-code"] = 0
                response["service_id"] = service_id
                response["ip"] = ip
                response["port"] = port
                sock.sendall(json.dumps(response).encode())
        
            else:
                print("closing connection to ", data.addr)
                sel.unregister(sock)
                sock.close()
        
    def start_shutdown_server(self):
        self.threads[shutdown_server_str] = threading.Thread(target=self.shutdown_server, daemon=True)
        self.threads[shutdown_server_str].start()

    def shutdown_server(self):
        HOST = ""
        PORT = 60002
        sel = selectors.DefaultSelector()

        # Create, bind, and listen on socket
        self.sockets[shutdown_server_str] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sockets[shutdown_server_str].bind((HOST, PORT))
        self.sockets[shutdown_server_str].listen()
        print("listening on", (HOST, PORT))
        self.sockets[shutdown_server_str].setblocking(False)

        # Select self.socks[shutdown_server] for I/O event monitoring 
        sel.register(self.sockets[shutdown_server_str], selectors.EVENT_READ, data=None)

        while True:
            # wait until selector is ready (or timeout expires)
            events = sel.select(timeout=None)

            # For each file object, process
            for key, mask in events:
                if key.data is None:
                    self.accept_connection(key.fileobj, sel)
                else:
                    self.mutex.acquire()
                    self.process_shutdown(key, mask, sel)
                    self.mutex.release()

    def process_shutdown(self, key, mask, sel):
        sock = key.fileobj
        data = key.data

        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(1024)
            if recv_data:
                # Receive and decode request
                print("Received" , repr(recv_data), "from", data.addr)
                raw_data = recv_data.decode()
                request = json.loads(raw_data)

                '''
                Request Format:
                {
                	"service_id": <service id of running application>,
            		"ip": <ip of device running application>,
			"port": <port for communication>
                }

                Response Format:
                {
                	"resp-code": <0 on success, -1 on failure>,
                	"failure-msg": <failure message>
                }
                '''
                
                response = {}
                # Check for invalid request
                if request["ip"] not in self.swarm.services:
                    response["resp-code"] = -1
                    response["failure-msg"] = "Invalid shutdown request: ip doesn't exist"
                    sock.sendall(json.dumps(response).encode())
                    return

                if request["service_id"] not in self.swarm.services[request["ip"]]:
                    response["resp-code"] = -1
                    response["failure-msg"] = "Invalid shutdown request: service_id doesn't exist"
                    sock.sendall(json.dumps(response).encode())
                    return
                
                # Shutdown application
                ip = request["ip"]
                service_id = request["service_id"]
                port = request["port"]
                
                resp = self.swarm.remove_service(ip, service_id)

                if resp is False:
                    response["resp-code"] = -1
                    response["failure-msg"] = "Failed to shutdown application"
                    sock.sendall(json.dumps(response).encode())
                    return

                # Send response
                response["resp-code"] = 0
                sock.sendall(json.dumps(response).encode())
        
            else:
                print("closing connection to ", data.addr)
                sel.unregister(sock)
                sock.close()
