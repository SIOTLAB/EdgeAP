import sys
import os
import docker
import json
import random

class DockerSwarm:

    '''
    	Class: DockerSwarm

	Member Variables:
   		config_file:
			Configuration containing the manager IP
			address (required) and information about
			remote nodes to be managed
		manager_ip: 
			IP address of the manager node
		manager_conn: 
			Docker connection object for the manager
		nodes:
    			Dictionary mapping IP of managed nodes to
			their docker connection object
		services:
			Dictionary mapping IP of managed nodes to
			list of services (dictionaries)
		ports:
			Dictionary mapping IP of managed nodes to
			list of ports used by services on that node
		join_token:
			Token used by worker nodes to join the swarm
    '''
    def __init__(self, config_file):
        self.config_file = config_file
        (manager_ip, managed_nodes) = read_config(config_file)
        self.manager_ip = manager_ip
        self.nodes = managed_nodes
        self.manager_conn = create_connection(remote=False)
        self.services = {}
        self.ports = {}
        # Initiate a new swarm, get the join token, and make
        # remote managed nodes join the swarm.
        # If a swarm already exists, restore previous state
        resp = self.init_swarm()
        self.join_token = self.get_worker_join_token()
        if resp is False:
            print("Swarm already exists. Restoring previous state")
            self.restore_old_swarm()
        else:
            for ip, conn in self.nodes.items():
                self.join_swarm(conn, ip)

    '''
	Function: 	init_swarm

	Description:	Initialize a new swarm and make this machine
			the manager node. Exit on error.
    '''
    def init_swarm(self):
        resp = None
        try:
            resp = self.manager_conn.init_swarm(advertise_addr=self.manager_ip)
        except docker.errors.APIError as e:
            print(e, file=sys.stderr)
            #sys.exit(-1)

        if resp is None:
            return False
        return True

    '''
    	Function:	restore_old_swarm

	Description:	Restore state from an existing swarm.
			Parse swarm information to update the
			nodes, services, and ports dicitionary.
			Save the join token.
    '''
    def restore_old_swarm(self):
        swarm_nodes = self.list_swarm_nodes(filters={"role":"worker"})
        ips_in_swarm = []
        for node in swarm_nodes:
            ips_in_swarm.append(node["Status"]["Addr"])

        # Only join swarm if not currently in the swarm
        for ip, conn in self.nodes.items():
            if ip not in ips_in_swarm:
                self.join_swarm(conn, ip)

        # Update services and ports
        services = self.get_services()
        for service in services:
            service_id = service["ID"]
            proxy_port = service["Endpoint"]["Spec"]["Ports"][0]["PublishedPort"]
            node_id = service["Spec"]["TaskTemplate"]["Placement"]["Constraints"][0]
            node_id = node_id[9:] # Hack: strip off "node.id=="
            server_ip = self.get_swarm_node(node_id=node_id)["Status"]["Addr"]
            if server_ip not in self.services:
                self.services[server_ip] = []
                self.ports[server_ip] = []
            self.services[server_ip].append(service_id)
            self.ports[server_ip].append(proxy_port)
    '''
	Function: 	inspect_swarm

	Description:	Return swarm information via a dictionary. 	
    '''
    def inspect_swarm(self):
        resp = False
        try:
            resp = self.manager_conn.inspect_swarm()
        except docker.errors.APIError as e:
            print(e, file=sys.stderr)

        return resp

    '''
    	Function: 	get_worker_join_token

	Description:	Return the worker join token for the swarm.
    '''
    def get_worker_join_token(self):
        try:
            return self.inspect_swarm()['JoinTokens']['Worker']
        except docker.errors.APIError as e:
            print(e, file=sys.stderr)

    '''
    	Function: 	join_swarm

	Description:	Make a remote node join the swarm. Must pass
			the IP of the node so that we can add it to
			the nodes dictionary. Return True on success, 
			False on failure.
    '''
    def join_swarm(self, client, server_ip):
        resp = False
        try:
            resp = client.join_swarm(remote_addrs=[self.manager_ip], join_token=self.join_token)
        except docker.errors.APIError as e:
            print(e, file=sys.stderr)

        if resp is not True:
            print("Error: Swarm join request unsuccessful", file=sys.stderr)
        elif server_ip not in self.nodes:
            # Add remote server to nodes dictionary
            self.nodes[server_ip] = {}
            self.nodes[server_ip]["client_conn"] = client
            #self.nodes[server_ip]["swarm_info"] = self.get_swarm_node(server_ip)
        return resp

    '''
    	Function: 	leave_swarm

	Description:	Make a node leave the swarm. If operating 
			on the manager node, force must be set to
    			True. Return True on success, False on failure.
    '''
    def leave_swarm(self, client, force=False):
        resp = False
        try:
            resp = client.leave_swarm(force)
        except docker.errors.APIError as e:
            print(e, file=sys.stderr)

        if resp is not True:
            print("Error: Swarm leave request unsuccessful", file=sys.stderr)
        return resp

    '''
    	Function: 	remove_node

	Description:	Remove node from being tracked by swarm.
    '''
    def remove_node(self, server_ip):
        resp = False
        try:
            swarm_node_id = self.get_swarm_node(server_ip)["ID"]
            resp = self.manager_conn.remove_node(swarm_node_id, force=True)
        except (docker.errors.APIError, docker.errors.NotFound) as e:
            print(e, file = sys.stderr)

        if resp is not True:
            print("Error: Removing node failed", file=sys.stderr)
        return resp

    '''
    	Function: 	shutdown_node

    	Description:	Remove the remote nodes from the swarm.
			Remove the manager node from the swarm.
    '''
    def shutdown_swarm(self):
        # Remove all remote nodes from swarm
        for ip, conn in self.nodes.items():
            self.leave_swarm(conn)
            self.remove_node(ip)

        # Remove Manager
        self.leave_swarm(self.manager_conn, force=True)
    
    '''
    	Function: 	list_swarm_nodes

	Description:	Return information on all nodes tracked by swarm.	
    '''
    def list_swarm_nodes(self, filters=None):
        resp = None
        try:
            resp = self.manager_conn.nodes(filters=filters)
        except docker.errors.APIError as e:
            print(e, file=sys.stderr)

        return resp

    '''
	Function:	get_swarm_node

	Description:	Return information on a specific swarm 
			node specified by either is IP address
			or swarm node id.
    '''
    def get_swarm_node(self, server_ip=None, node_id=None, filters=None):
        if server_ip == None and node_id == None:
            return None
        nodes = self.list_swarm_nodes(filters=filters)
        for node in nodes:
            if (node_id is not None and node["ID"]==node_id):
                return node
            elif (node["Status"]["Addr"]==server_ip):
                return node
        return None

    '''
	Function:	create_container

	Description:	Create a swarm service, with one replica and 
			placed on the specific worker node specified by
			'server_ip'. Port mapping is also configured
			mapping a port on the host to a port on the 
			container.
    '''
    def create_service(self, server_ip, request):

        # Specify access to container via port mapping
        proxy_port = self.generate_port_num(server_ip)
        container_port = request["application_port"]
        protocol = request["protocol"]
        publish_mode = 'host'
        port_config_tuple = (container_port, protocol,publish_mode)
        port_config_dict = {proxy_port: port_config_tuple}
        endpoint_spec = docker.types.EndpointSpec(ports=port_config_dict)

        #proxy_port = None
        #endpoint_spec = None
        
        # Specify image to run and options
        container_spec = docker.types.ContainerSpec(image=request["image"],
        					     tty=True)

        # Specify where to place the container
        swarm_node_id = self.get_swarm_node(server_ip)["ID"]
        placement = docker.types.Placement(constraints=["node.id=={}".format(swarm_node_id)])

        # Complete service configuration
        task_template = docker.types.TaskTemplate(container_spec=container_spec,
        				          resources=None,
        				          placement=placement)

        # Create the service
        try:
            service_key = self.manager_conn.create_service(task_template=task_template,
                                                endpoint_spec=endpoint_spec)
        except docker.errors.APIError as e:
            print(e, file=sys.stderr)
            return(False, None)

        if server_ip not in self.services:
            self.services[server_ip] = []
            self.ports[server_ip] = []

        #service_info = self.get_service_info(service_key["ID"])

        self.services[server_ip].append(service_key["ID"])
        if proxy_port is not None:
            self.ports[server_ip].append(proxy_port)
        return (True, service_key["ID"])

    '''
    	Function:	remove_service

	Description:	Remove a service specified by service_id.
			Remove the service and related ports from 
			being tracked by the services and ports
			data structures.
    '''
    def remove_service(self, server_ip, service_id):
        service_info = self.get_service_info(service_id)
        resp = False
        try:
            resp = self.manager_conn.remove_service(service_id)
        except docker.errors.APIError as e:
            print(e, file=sys.stderr)

        if resp is not True:
            print("Error: Removing service was unsuccessful", file=sys.stderr)
            return False
        else:
            # delete service from service dictionary
            try:
                self.services[server_ip].remove(service_id)
            except (KeyError, ValueError) as e:
                print(e, file=sys.stderr)
                print("Error while removing service id from swarm object")
            print(self.services[server_ip])

            # delete port from ports dictionary
            try:
                port = service_info["Spec"]["EndpointSpec"]["Ports"][0]["PublishedPort"]
                self.ports[server_ip].remove(port)
            except ValueError as e:
                print(e, file=sys.stderr)
                print("Error while removing port number from swarm object", file=sys.stderr)
                
            return True

    '''
	Function:	get_services

	Description:	Get all services currently managed by the swarm.
			Returns a list of dictionaries containing data
			about each service.
    '''
    def get_services(self):
        try:
            resp = self.manager_conn.services()
        except docker.errors.APIError as e:
            print(e, file=sys.stderr)
            return None

        return resp

    '''
    	Function:	get_service_info

	Description:	Return a dictionary containing information
			about a swarm service.
    '''
    def get_service_info(self, service_id):
        resp = None
        try:
            resp = self.manager_conn.inspect_service(service_id)
        except docker.errors.APIError as e:
            print(e, file=sys.stderr)
            
        if resp is None:
            print("Error: Getting service info failed", file=sys.stderr)
        return resp

    '''
	Function:	generate_port_num

	Description:	Generate a random port number in the range
			50000-60000, which is a subset of the ephemeral port
			range for Linux machines.
    '''
    def generate_port_num(self, server_ip):
        port = random.randint(50000,60000)

        if (server_ip not in self.ports):
            return port

        while(port in self.ports[server_ip]):
            port = random.randint(50000,60000)
        return port

# ------------------------ Helper Functions ------------------------#

'''
	Function:	read_config

	Description:	Read and parse configuration file.
			Return a tuple (string,dictionary)
			containing the manager node IP address
			and a dictionary for all the managed
			nodes (key: IP, value: swarm connection object).
'''
def read_config(config_file):

    if not os.path.isfile(config_file):
        print("Error: config file {} does not exist".format(config_file), file=sys.stderr)
        sys.exit(-1)
    
    with open(config_file, "r") as f:
        config = json.load(f)

    manager_ip = ""
    managed_nodes = {}
    try:
        # Get manager_ip
        manager_ip = config["manager_ip"]
        # Find configuration for remote managed nodes
        # Extract necessary info like ip, port, and tlsconfig
        if "remotes" in config:
            for ip, d in config["remotes"].items():
                port = d["port"]
                if d["tlsverify"] == True:
                    certs_path = d["certs_path"]
                    ca_cert = d["tlscacert"]
                    client_cert = d["tlscert"]
                    client_key = d["tlskey"]
                    tls_config = docker.tls.TLSConfig(
                        verify=True,
                        ca_cert=os.path.join(certs_path,ca_cert),
                        client_cert=(os.path.join(certs_path,client_cert),
                                     os.path.join(certs_path,client_key)),
                    )
                # Create Docker Swarm remote connection object
                remote_conn = create_connection(True,ip,port,tls_config)
                # Add IP and remote_conn to the dictionary
                managed_nodes[ip] = remote_conn
    except Exception as e:
        print(e, file=sys.stderr)
        print("Error: error while parsing config file", file=sys.stderr)
        sys.exit(-1)

    return (manager_ip, managed_nodes)
            
'''
	Function:	create_connection

	Description:	Create a new Docker Swarm connection object.
			Remote connections must specify an ip and port.
'''
def create_connection(remote=False,ip=None, port=None, tls_config=None):
    client = None
    if (remote == True):
        try:
            client = docker.APIClient(base_url='tcp://{}:{}'.format(ip,port),
                                      tls=tls_config
            )
        except docker.errors.DockerException as e:
            print(e, file=sys.stderr)
    else:
        try:
            client = docker.APIClient(base_url='unix://var/run/docker.sock')
        except docker.erros.DockerException as e:
            print(e, file=sys.stderr)
            sys.exit(-1)

    return client

def get_version(client):
    try:
        return client.version()
    except Exception as e:
        print(e, file=sys.stderr)

def get_images(client):
    try:
        return client.images()
    except docker.errors.APIError as e:
        print(e, file=sys.stderr)
        return None
        
def get_containers(client):
    try:
        return client.containers()
    except docker.errors.APIError as e:
        print(e, file=sys.stderr)
        return None
