import json
import requests
from requests.auth import HTTPBasicAuth

almUserName = "{USERNAME}"
almPassword = "{PASSWORD}"
almDomain = "{DOMAIN}"
almProject = "{PROJECT}"

almURL = "{ALM_URL}"  # eg., http://192.168.0.1:8080/qcbin/"
authEndPoint = almURL + "authentication-point/authenticate"
qcSessionEndPoint = almURL + "rest/site-session"
qcLogoutEndPoint = almURL + "authentication-point/logout"
midPoint = "rest/domains/" + almDomain + "/projects/" + almProject + "/"

run_id = ""
execution_status = ""

cookies = dict()

headers = {
    'cache-control': "no-cache",
    'Accept': "application/json",
    'Content-Type': "application/json"
}


def alm_login():
    """
    Function    :   alm_login
    Description :   Authenticate user
    Parameters  :   global parameter
                    alm_username     -   ALM User
                    alm_password     -   ALM Password
    """
    response = requests.post(authEndPoint, auth=HTTPBasicAuth(almUserName, almPassword), headers=headers)
    if response.status_code == 200:
        cookieName = response.headers.get('Set-Cookie')
        LWSSO_COOKIE_KEY = cookieName[cookieName.index("=") + 1: cookieName.index(";")]
        cookies['LWSSO_COOKIE_KEY'] = LWSSO_COOKIE_KEY
        print('logged in succesfully')
    response = requests.post(qcSessionEndPoint, headers=headers, cookies=cookies)
    if response.status_code == 200 or response.status_code == 201:
        cookieName = response.headers.get('Set-Cookie').split(",")[1]
        QCSession = cookieName[cookieName.index("=") + 1: cookieName.index(";")]
        cookies['QCSession'] = QCSession
    return



def alm_logout():
    """
    Function    :   alm_logout
    Description :   terminate user session
    Parameters  :   No Parameters
    """
    response = requests.post(qcLogoutEndPoint, headers=headers, cookies=cookies)
    print(response.headers.get('Expires'))
    return


def get_test_details(cycleid, testid, exec_status):
    """
    Function    :   get_test_details
    Description :   get all the details required to construct Create test run payload.
    Parameters  :   cycleid = This is Test Set ID where we need to update results
                    testid = This is ALM test ID of the test case we need to update the result
                    exec_status = result of test execution {Passed,Failed, No run, Not Completed}
    :return:
    """
    global execution_status
    execution_status = exec_status
    qcalltestEndoint = almURL + midPoint + "test-instances?query={cycle-id[" + cycleid + "];test-id[" + testid + "]}"
    response = requests.get(qcalltestEndoint, headers=headers, cookies=cookies).json()
    construct_test_run_payload(response['entities'][0])


def construct_test_run_payload(detdict):
    req_keys = ['test-id', 'cycle-id', 'name', 'status', 'subtype-id', 'owner', 'test-instance', 'testcycl-id', 'id']
    payload_list = [x for x in detdict['Fields'] if not x['Name'] not in req_keys]
    for element in payload_list:
        if element['Name'] == 'subtype-id':
            element['values'][0]['value'] = "hp.qc.run.MANUAL"
        if element['Name'] == 'status':
            element['values'][0]['value'] = "Not Completed"
        if element['Name'] == 'owner':
            element['values'][0]['value'] = "AAARES"
        if element['Name'] == 'id':
            element['Name'] = 'testcycl-id'
    detdict['Fields'] = payload_list
    detdict['Type'] = 'run'
    create_Test_Run(detdict)


def create_Test_Run(payload):
    global run_id
    jsondata = json.dumps(payload)
    qccreaterunEndoint = almURL + midPoint + "/runs"
    response = requests.post(qccreaterunEndoint, headers=headers, cookies=cookies, data=jsondata).json()
    for element in response['Fields']:
        if element['Name'] == 'id':
            run_id = element['values'][0]['value']
            print(run_id)
            print('\n')
    construct_update_test_run_payload(response)


def construct_update_test_run_payload(detdict):
    req_keys = ['execution-date', 'ver-stamp', 'test-config-id', 'name', 'has-linkage', 'host', 'testcycl-id', 'status',
                'subtype-id', 'draft', 'duration', 'owner']
    payload_list = [x for x in detdict['Fields'] if not x['Name'] not in req_keys]
    for element in payload_list:
        if element['Name'] == 'host':
            element['values'][0] = {'value': "Automation"}
        if element['Name'] == 'status':
            element['values'][0]['value'] = execution_status
    detdict['Fields'] = payload_list
    update_TestRun_result(detdict)


def update_TestRun_result(payload):
    jsondata = json.dumps(payload)
    qcupdateresultEndoint = almURL + midPoint + "runs/" + run_id
    print(qcupdateresultEndoint)
    print('\n')
    response = requests.put(qcupdateresultEndoint, headers=headers, cookies=cookies, data=jsondata)
    all_tests = json.loads(response.text)
