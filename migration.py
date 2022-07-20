import os
import requests
import json
import random
import time

api_key = os.environ.get('API_KEY',"")
team_name = os.environ.get('TEAM_NAME',"")
user_id = os.environ.get('USER_ID',"")




team_url = 'https://www.zenduty.com/api/account/teams/'
team_members_url = 'https://www.zenduty.com/api/account/teams/{}/members/'
team_schedule_url= 'https://www.zenduty.com/api/account/teams/{}/schedules/'
team_escalation_policy_url = 'https://www.zenduty.com/api/account/teams/{}/escalation_policies/'
team_sla_url = "https://www.zenduty.com/api/account/teams/{}/sla/"
sla_detail_url = "https://www.zenduty.com/api/account/teams/{}/sla/{}/"
team_task_template_url = "https://www.zenduty.com/api/account/teams/{}/task_templates/"
team_priority_url = "https://www.zenduty.com/api/account/teams/{}/priority/"
team_service_url = "https://www.zenduty.com/api/account/teams/{}/services/"
service_integration_url =  "https://www.zenduty.com/api/account/teams/{}/services/{}/integrations/"
team_tags_url = "https://www.zenduty.com/api/account/teams/{}/tags/"
team_maintenance_window_url = "https://www.zenduty.com/api/account/teams/{}/maintenance/"
team_incident_roles_url = "https://www.zenduty.com/api/account/teams/{}/roles/"
alert_rule_url = "https://www.zenduty.com/api/account/teams/{}/services/{}/integrations/{}/transformers/"
 
def get_team_unique_id():
    
    res = requests.get('{}'.format(team_url), headers={'Authorization': 'Token {}'.format(api_key)})
    if res.status_code == 200:
        unique_ids = [team["unique_id"] for team in res.json()]
        return unique_ids
    raise Exception("Error: {}".format(res.status_code))

def get_or_create_team(team):
    res = requests.get('{}'.format(team_url), headers={'Authorization': 'Token {}'.format(api_key)})
    
    if res.status_code == 200:
        for team in res.json():
            if team['name'].lower() == team_name.lower():
                return team['unique_id']
        res1 = requests.post('{}'.format(team_url), data={'name': team_name}, headers={'Authorization': 'Token {}'.format(api_key)})
        return res1.json()['unique_id']
    
    raise Exception("Error: {}".format(res.status_code))

def send_request(url):
    time.sleep(0.3)
    res = requests.get('{}'.format(url), headers={'Authorization': 'Token {}'.format(api_key),"Content-type":"application/json"})
    if res.status_code == 200:
        return res.json()
    raise Exception("Error: {}".format(res.status_code))


def add_team_members(team_ids,team_id):
    
    
    get_existing_team_member = send_request('{}'.format(team_members_url.format(team_id)))
    
    existing_team_members_ids = [member['user']['username'] for member in get_existing_team_member]
    
    for team in team_ids:
        # migrate team members
        team_members = send_request('{}'.format(team_members_url.format(team)))

        for member in team_members:
            if member['user']['username'] not in existing_team_members_ids:
                res = requests.post('{}'.format(team_members_url.format(team_id)),data=json.dumps({'team':team,'user':member['user']['username'],"role": member['role']}) ,headers={'Authorization': 'Token {}'.format(api_key),"Content-type":"application/json"})
                if res.status_code != 201 and res.json() !=  ['User already exists'] :
                    print("error in adding user to team status:{},error:{},email:{}".format(res.status_code,str(res.json()),member['user']['email']))
                if res.status_code == 201:
                    print("user added to team:{}".format(member['user']['username']))
                    
    print('team members added successfully')

def write_json(filename, data):
    
        # logger.info("Writing to {}".format(filename))
    existing_data = read_json(filename)
    existing_data.update(data)
    # print(existing_data)
    with open(filename, mode="w") as log_file:
        log_file.write(json.dumps(existing_data,indent=4))

def read_json(filename): 
    # logger.info("Reading from {}".format(filename))
    with open(filename, mode="r") as log_file:
        return json.loads(log_file.read())

def migrate_schedule(team_ids,team_id):
   
    existing_schedule_ids = read_json('mapping.json')
    existing_schedule_ids  = list(existing_schedule_ids.keys())
    # print(existing_schedule_ids)
    for team in team_ids:
        get_schedules = send_request('{}'.format(team_schedule_url.format(team)))
        for schedule in get_schedules:
            if schedule['unique_id'] not in existing_schedule_ids:
                schedule['team'] = team_id
                for layer in schedule['layers']:
                    del layer['unique_id']
                    for restriction in layer['restrictions']:
                        del restriction['unique_id']
                    for user in layer['users']:
                        del user['unique_id']
                
                for override in schedule['overrides']:
                    del override['unique_id']
                
                
                
                res = requests.post('{}'.format(team_schedule_url.format(team_id)),data=json.dumps(schedule) ,headers={'Authorization': 'Token {}'.format(api_key),"Content-type":"application/json"})
                if res.status_code != 201:
                    print("error in adding schedule to team status:{},error:{},name:{}".format(res.status_code,str(res.json()),schedule['name']))
                if res.status_code == 201:
                    write_json('mapping.json',{schedule['unique_id']:res.json()['unique_id']})
                    print("schedule added to team:{}".format(schedule['name']))
    
                

                #write to file old schedule id and new schedule id
            
        
    
    print('schedule added successfully')    

def migrate_escalation_policy(team_ids,team_id):
    existing_mapping = read_json("mapping.json")
    existing_escalation_policy_ids = list(existing_mapping.keys())
    for team in team_ids:
        get_ep = send_request('{}'.format(team_escalation_policy_url.format(team)))
        for ep in get_ep:
            
            if ep["unique_id"] not in existing_escalation_policy_ids:
                
                print("escalation policy added to team:{}".format(ep['name']))
                if  ep['name'] == "Default Escalation Policy":
                    ep['name'] = "{}-{}".format(ep['name'], team[0:8]) 
                
                ep['team'] = team_id
                ep["description"] = "some description" if ep['description'] == None or ep['description'] == "" else ep['description']
                
                for rule in ep['rules']:
                    
                    for target in rule['targets']:
                        try:
                            if target['target_type'] == 1:
                                target["target_id"] = existing_mapping[target['target_id']]
                        except Exception as e:
                            del target
                            
                    if len(rule['targets']) == 0:
                        rule['targets'].append({'target_type':2,'target_id':user_id})

                res = requests.post('{}'.format(team_escalation_policy_url.format(team_id)),data=json.dumps(ep) ,headers={'Authorization': 'Token {}'.format(api_key),"Content-type":"application/json"})
                if res.status_code != 201:
                    print("error in adding esp to team status:{},error:{},name:{}".format(res.status_code,str(res.json()),ep['name']))
                if res.status_code == 201:
                    write_json("mapping.json",{ep['unique_id']:res.json()['unique_id']})
                    print("escalation policy added to team:{}".format(ep['name']))
                    
    print('escalation policy added successfully')
    

def migrate_slas(team_ids,team_id):
    existing_mapping = read_json("mapping.json")
    existing_sla_ids = list(existing_mapping.keys())
    for team in team_ids:
        get_sla = send_request('{}'.format(team_sla_url.format(team)))
        for sla in get_sla:
            if sla["unique_id"] not in existing_sla_ids:
                get_sla_details = send_request('{}'.format(sla_detail_url.format(team,sla['unique_id'])))
                try:
                    get_sla_details.pop('team')
                except:
                    pass
                res = requests.post('{}'.format(team_sla_url.format(team_id)),data=json.dumps(get_sla_details) ,headers={'Authorization': 'Token {}'.format(api_key),"Content-type":"application/json"})    
                if res.status_code != 201:
                    print("error in adding slas to team status:{},error:{},name:{}".format(res.status_code,str(res.json()),sla['name']))
                if res.status_code == 201:
                    write_json("mapping.json",{sla['unique_id']:res.json()['unique_id']})
                    print("sla added to team:{}".format(sla['name']))
    
    print("slas migrated successfully")
    
def migrate_task_templates(team_ids,team_id):
    existing_mapping = read_json("mapping.json")
    existing_mapping_task_ids = list(existing_mapping.keys())
    
    for team in team_ids:
        get_task_templates = send_request('{}'.format(team_task_template_url.format(team)))
        
        for task_template in get_task_templates:
            if task_template["unique_id"] not in existing_mapping_task_ids:
                task_template['team'] = team_id
                res = requests.post('{}'.format(team_task_template_url.format(team_id)),data=json.dumps(task_template) ,headers={'Authorization': 'Token {}'.format(api_key),"Content-type":"application/json"})
                if res.status_code != 201:
                    print("error in adding task_templates to team status:{},error:{},name:{}".format(res.status_code,str(res.json()),task_template['name']))
                if res.status_code == 201:
                    write_json("mapping.json",{task_template['unique_id']:res.json()['unique_id']})
                    
                    print("task_templates added to team:{}".format(task_template['name']))

    print('task templates added successfully')
    
def migrate_priorities(team_ids,team_id):
    existing_mapping = read_json("mapping.json")
    existing_prioritie_ids = list(existing_mapping.keys())
    for team in team_ids:
        get_priorities = send_request('{}'.format(team_priority_url.format(team)))
        for priority in get_priorities: 
            if priority["unique_id"] not in existing_prioritie_ids:
                priority['team'] = team_id
                priority['color'] = "black" if priority['color'] == None or priority['color'] == "" else priority['color']
                res = requests.post('{}'.format(team_priority_url.format(team_id)),data=json.dumps(priority) ,headers={'Authorization': 'Token {}'.format(api_key),"Content-type":"application/json"})
                if res.status_code != 201:  
                    print("error in adding  priorities to team status:{},error:{},name:{}".format(res.status_code,str(res.json()),priority['name']))
                if res.status_code == 201:
                    write_json("mapping.json",{priority['unique_id']:res.json()['unique_id']})
                    
                    print("priorities added to team:{}".format(priority['name']))
        
    print('priorities added successfully')

def migrate_services(team_ids,team_id):
    existing_mapping = read_json("mapping.json")
    existing_service_ids = list(existing_mapping.keys())
    for team in team_ids:
        get_services = send_request('{}'.format(team_service_url.format(team)))
        
        for service in get_services: 
            if service["unique_id"] not in existing_service_ids:
                service['team'] = team_id
                service['team_priority'] = service['team_priority'] if service['team_priority'] == None else existing_mapping[service['team_priority']]
                service['sla'] = service['sla'] if service['sla'] == None else existing_mapping[service['sla']]
                service['task_template'] = None if service['task_template'] == None else existing_mapping[service['task_template']]
                service['escalation_policy'] = None if service['escalation_policy'] == None else existing_mapping[service['escalation_policy']]
                service['description'] = "some description" if service['description'] == None or service['description'] == "" else service['description']
                get_integrations = send_request('{}'.format(service_integration_url.format(team,service['unique_id'])))
                
                old_outgoing_integrations = []
                old_zen_integrations = []
                
                integrations = []
                for integration in get_integrations:
                    # integration.pop('service_id')
                    # integration['service_id'] = res.json()['unique_id']
                    if  integration['application'] != None:
                        
                        if integration['application_reference']['application_type'] == 0:
                            old_zen_integrations.append(integration['unique_id'])
                            
                        elif integration['application_reference']['application_type'] == 1:
                            old_outgoing_integrations.append(integration['unique_id'])
                        else: 
                            continue
                        

                        integrations.append({ "application": integration['application'], "name": "some integration" if integration['name']==None or integration['name']=="" else integration['name']})
                
                if len(integrations)  > 0:
                    service['integrations'] = integrations
                res = requests.post('{}'.format(team_service_url.format(team_id)),data=json.dumps(service) ,headers={'Authorization': 'Token {}'.format(api_key),"Content-type":"application/json"})
                
                if res.status_code != 201:
                    print("error in adding services to team status:{},error:{},name:{}".format(res.status_code,str(res.json()),service['name']))
                if res.status_code == 201:
                    write_json("mapping.json",{service['unique_id']:res.json()['unique_id']})  
                    # get new integrations
                    new_zen_integrations = []
                    new_outgoing_integrations = []
                    
                    
                    new_integrations = send_request('{}'.format(service_integration_url.format(team_id,res.json()['unique_id'])))
                    for integration in new_integrations:
                        if integration['application_reference']['application_type'] == 0:
                            new_zen_integrations.append(integration['unique_id'])
                        elif integration['application_reference']['application_type'] == 1:
                            new_outgoing_integrations.append(integration['unique_id'])
                    zen_dict = dict(zip(old_zen_integrations,new_zen_integrations))
                    outgoing_dict = dict(zip(old_outgoing_integrations,new_outgoing_integrations))
                    zen_dict.update(outgoing_dict)
                    
                    write_json("mapping.json",zen_dict)
                    
                    all_integrations = old_outgoing_integrations + old_zen_integrations
                    for migrate_integration in all_integrations:
                        get_alert_rules = send_request('{}'.format(alert_rule_url.format(team,service['unique_id'],migrate_integration)))
                        for alert_rule in get_alert_rules:
                            del alert_rule['unique_id']
                            for action in alert_rule['actions']: 
                                action['escalation_policy'] = None if action['escalation_policy'] == None  else existing_mapping[action['escalation_policy']]
                                action['key'] = None if action['key'] == None or action['key'] == "" else existing_mapping[action['key']]
                                action['schedule'] = None if action['schedule'] == None else existing_mapping[action['schedule']]
                                action['sla'] = None if action['sla'] == None else existing_mapping[action['sla']]
                                action['team_priority'] = None if action['team_priority'] == None else existing_mapping[action['team_priority']]
                                del action['unique_id']
                            alert_rule['actions'] = alert_rule['actions']
                            create_alert_rule = requests.post('{}'.format(alert_rule_url.format(team_id,res.json()['unique_id'],zen_dict[migrate_integration])),data=json.dumps(alert_rule) ,headers={'Authorization': 'Token {}'.format(api_key),"Content-type":"application/json"})
                            if create_alert_rule.status_code != 201:
                                print("error in adding alert rule to service status:{},error:{},name:{}".format(create_alert_rule.status_code,str(create_alert_rule.json()),alert_rule['description']))
                            if create_alert_rule.status_code == 201:
                                print("alert rule added to integration:{}".format(alert_rule['description']))
                                
                    print("services added to team:{}".format(service['name']))
                
    print('services added successfully')
    

def migrate_tags(team_ids,team_id):
    existing_mapping = read_json("mapping.json")
    for team in team_ids:
        get_team_tags = send_request('{}'.format(team_tags_url.format(team)))
        for tag in get_team_tags:
            if tag["unique_id"] in existing_mapping:
                id = tag['unique_id']
                tag['team'] = team_id
                tag['color'] = "black" if tag['color'] == None or tag['color'] == "" else tag['color']
                del tag['unique_id']
                res = requests.post('{}'.format(team_tags_url.format(team_id)),data=json.dumps(tag) ,headers={'Authorization': 'Token {}'.format(api_key),"Content-type":"application/json"})
                if res.status_code != 201:  
                    print("error in adding  tags to team status:{},error:{},name:{}".format(res.status_code,str(res.json()),tag['name']))
                if res.status_code == 201:
                    write_json("mapping.json",{id:res.json()['unique_id']})
                    
                    print("tags added to team:{}".format(tag['name']))
    print("tags added successfully")
                
def migrate_maintenance_window(team_ids,team_id):
    existing_mapping = read_json("mapping.json")
    existing_mapping_maintenance_window_ids = list(existing_mapping.keys())
    for team in team_ids:
        get_team_maintenance_window = send_request('{}'.format(team_maintenance_window_url.format(team)))
        
        for maintenance_window in get_team_maintenance_window:
            
            if maintenance_window['unique_id'] not in existing_mapping_maintenance_window_ids:
               
                maintenance_window['team'] = team_id
                new_maintenance = []
                
                for maintenance in maintenance_window['services']:
                    try:
                        new_maintenance.append({'service': existing_mapping[maintenance['service']]})
                    except Exception as e:
                        print(str(e))
                    
                maintenance_window['services'] = new_maintenance
                id =  maintenance_window['unique_id']
                del maintenance_window['unique_id']
                
                res = requests.post('{}'.format(team_maintenance_window_url.format(team_id)),data=json.dumps(maintenance_window) ,headers={'Authorization': 'Token {}'.format(api_key),"Content-type":"application/json"})
                if res.status_code != 201:  
                    print("error in adding  maintenance to team status:{},error:{},name:{}".format(res.status_code,str(res.json()),maintenance_window['name']))
                if res.status_code == 201:
                    write_json("mapping.json",{id:res.json()['unique_id']})
                    print("maintenance added to team:{}".format(maintenance_window['name']))
                    
    print("maintenance added successfully")

def migrate_incident_roles(team_ids,team_id):
    existing_mapping = read_json("mapping.json")
    existing_mapping_incident_roles_ids = list(existing_mapping.keys())
    names = ['incident commander']
    for team in team_ids:
        get_incident_roles = send_request('{}'.format(team_incident_roles_url.format(team)))
        for incident_role in get_incident_roles:
            if incident_role['unique_id'] not in existing_mapping_incident_roles_ids:
                id = incident_role['unique_id']
                if incident_role['title'].lower() in names:
                    incident_role['title'] ="{}{}".format(incident_role['title'],str(random.randint(1,10000)))
                del incident_role['unique_id']
                incident_role['team'] = team_id
                
                res = requests.post('{}'.format(team_incident_roles_url.format(team_id)),data=json.dumps(incident_role) ,headers={'Authorization': 'Token {}'.format(api_key),"Content-type":"application/json"})
                if res.status_code != 201:
                    print("error in adding  incident roles to team status:{},error:{},name:{}".format(res.status_code,str(res.json()),incident_role['title']))
                if res.status_code == 201:
                    write_json("mapping.json",{id:res.json()['unique_id']})
                    print("incident roles added to team:{}".format(incident_role['title']))
    
    print("incident roles added successfully")
        
    
def migrate(): 
    
    # should be executed in sequence
    
    new_team_id = get_or_create_team(team_name)
    
    team_ids = get_team_unique_id()
    
    if new_team_id in team_ids:
        team_ids.remove(new_team_id)
    
 
    add_team_members(team_ids,new_team_id)
    migrate_schedule(team_ids,new_team_id)
    migrate_escalation_policy(team_ids,new_team_id)
    migrate_slas(team_ids,new_team_id)
    migrate_task_templates(team_ids,new_team_id)
    migrate_priorities(team_ids,new_team_id)
   
    migrate_tags(team_ids,new_team_id)
    migrate_incident_roles(team_ids,new_team_id)
    migrate_services(team_ids,new_team_id)
    
    migrate_maintenance_window(team_ids,new_team_id)
    
    

migrate()

    