import sys
import os
import json
import docker
import swarm

config_file = "manager.conf"

def main():
    
    # Create swarm object
    swarm_obj = swarm.DockerSwarm(config_file)

    # Print out swarm info
    #print(json.dumps(swarm_obj.list_swarm_nodes(), indent=3))

    # Create service
    request = {"image": "ubuntu",
               "application_port": 4000,
               "protocol": "tcp"
               }
    (resp, service_id) = swarm_obj.create_service("172.0.0.1", request)

    # Print out service info
    print(json.dumps(swarm_obj.get_service_info(service_id), indent=3))
    #services = swarm_obj.get_services()
    #for service in services:
    #    print(json.dumps(service, indent=3))

    # Remove service
    #service_id = swarm_obj.services["172.0.0.1"][0]
    resp = swarm_obj.remove_service("172.0.0.1", service_id)
    print(swarm_obj.services)
    print(swarm_obj.ports)

    # Shutdown swarm
    swarm_obj.shutdown_swarm()
    

if __name__ == "__main__":
    main()
