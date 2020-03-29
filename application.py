import requests
import os
from flask import Flask, request, abort, app, jsonify, json
from sqlalchemy.orm.exc import NoResultFound
from twilio.rest import Client
from flask_sqlalchemy import SQLAlchemy
from repo.database_setup import User, BankAccount, Base

# EB looks for an 'application' callable by default.
from repo.populate import insert_seed_data

application = Flask(__name__)

application.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coronials-collection.db'
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
application.config['SQLALCHEMY_ECHO'] = True

db = SQLAlchemy(application)

SETTINGS_ENABLE_SMS = True
NEW_LINE = '\r\n'
API_BASE_PATH = os.environ['EB_BASE_PATH']
DEST_TYPE_MENU = "MENU"
DEST_TYPE_TASK = "TASK"
SUCCESSFUL_REGISTRATION_MSG = 'Thank for registering ✅\n' \
                              'You can go back 🏃‍♂ to the main menu by replying with:\n' \
                              '"Back" 😁'

# Twilio Dinges make these environment vars
account = "TwilioAccountID"
token = "TwilioAccountToken"
client = Client(account, token)


# End Twilio Dinges

# @Richard TODO User management
# Put your stuff here

# User management
@application.route('/api/v1/user/<string:user_identifier>', methods=['GET'])
def get_user_by_identifier_api(user_identifier):
    if user_identifier is None:
        response = jsonify({
            'message': 'Missing request parameter: "user_identifier"'
        })
        return response, 400

    try:
        user = get_user_by_user_identifier(user_identifier)
    except NoResultFound:
        response = jsonify({
            'message': 'No user exists'
        })
        return response, 404

    response = jsonify({
        'user': user.serialize()
    })
    return response, 200


@application.route('/api/v1/user', methods=['POST'])
def create_base_user():
    data = request.json

    if 'user_identifier' in data:
        user_identifier = data['user_identifier']
    else:
        response = jsonify({
            'message': 'Missing request parameter: "user_identifier"'
        })
        return response, 400

    if 'name' in data:
        name = data['name']
    else:
        response = jsonify({
            'message': 'Missing request parameter: "name"'
        })
        return response, 400

    # CHECK IF USER ALREADY REGISTERED
    try:
        get_user_by_user_identifier(user_identifier)
        response = jsonify({
            'message': 'User already registered'
        })
        return response, 400
    except NoResultFound:
        pass

    # CREATE USER
    user = User()
    user.name = name
    user.user_identifier = user_identifier

    db.session.add(user)
    db.session.commit()

    response = jsonify({
        'id': user.id
    })

    return response, 201


@application.route('/api/v1/user/id_number', methods=['POST'])
def set_user_id_number():
    data = request.json

    if 'user_identifier' in data:
        user_identifier = data['user_identifier']
    else:
        response = jsonify({
            'message': 'Missing request parameter: "user_identifier"'
        })
        return response, 400

    if 'id_number' in data:
        id_number = data['id_number']
    else:
        response = jsonify({
            'message': 'Missing request parameter: "name"'
        })
        return response, 400

    try:
        user = get_user_by_user_identifier(user_identifier)
    except NoResultFound:
        response = jsonify({
            'message': 'No user exists'
        })
        return response, 404

    user.id_number = id_number

    db.session.add(user)
    db.session.commit()

    response = jsonify({
        'user': user.serialize()
    })
    return response, 200


@application.route('/api/v1/user/<string:user_identifier>/bank_account', methods=['GET'])
def get_bank_accounts(user_identifier):
    if user_identifier is None:
        response = jsonify({
            'message': 'Missing request parameter: "user_identifier"'
        })
        return response, 400

    try:
        user = get_user_by_user_identifier(user_identifier)
    except NoResultFound:
        response = jsonify({
            'message': 'No user exists'
        })
        return response, 404

    bank_accounts = user.bankaccounts

    response = jsonify({
        'bank_accounts': [bankacc.serialize() for bankacc in bank_accounts]
    })
    return response, 200


@application.route('/api/v1/user/bank_account', methods=['POST'])
def add_bank_details():
    data = request.json

    if 'user_identifier' in data:
        user_identifier = data['user_identifier']
    else:
        return create_missing_identifier_response('user_identifier'), 400

    if 'bank' in data:
        bank = data['bank']
    else:
        return create_missing_identifier_response('bank'), 400

    if 'accno' in data:
        accno = data['accno']
    else:
        return create_missing_identifier_response('accno'), 400

    if 'branch' in data:
        branch = data['branch']
    else:
        branch = None

    try:
        user = get_user_by_user_identifier(user_identifier)
    except NoResultFound:
        response = jsonify({
            'message': 'No user exists'
        })
        return response, 404

    bankacc = BankAccount()
    bankacc.bank = bank
    bankacc.accno = accno
    bankacc.branch = branch

    user.bankaccounts.append(bankacc)

    db.session.add(user)
    db.session.add(bankacc)
    db.session.commit()

    response = jsonify({
        'id': bankacc.id
    })
    return response, 201

back_menu_store = {}
# back_menu_stack = {}

menus = {}

### TEAM INFO around how to use menu system
# -> Main Menu is defined at the root as menus['main'] see below
# -> To add a new menu, create menus['menu-name'] = {} use menus['main'] or menus['business'] as example
# -> To link to a menu use DEST_TYPE_MENU type and set value to menu as defined here. EG menus['business']
# -> To link to a task defined in twilio, use DEST_TYPE_TASK type and set value to task as defined in twilio

menus['main'] = {
    'intro': "Please select an option below. Are you:",
    'options': [
        {
            'friendly': '👱 An individual',
            'dest': {
                'type': DEST_TYPE_MENU,
                'value': 'individual'
            },
        },
        {
            'friendly': '💼 A business',
            'dest': {
                'type': DEST_TYPE_MENU,
                'value': 'business'
            },
        },
        {
            'friendly': 'ℹ️ Get information',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'help'
            },
        },
    ]
}

menus['business'] = {
    'intro': "We have gathered all the business information that may be applicable to you.",
    'options': [
        {
            'friendly': '👷‍♀️ Employee Tax Incentive',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'business_employee_tax_incentive'
            },
        },
        {
            'friendly': '💵 Compensation Fund',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'business_compensation_fund'
            },
        },
        {
            'friendly': '👩🏼‍🏭 Temporary Employee Relief Scheme',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'business_temporary_employee_relief_scheme'
            },
        },
        {
            'friendly': '🏧 Business Loans',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'business_loans'
            },
        },
        {
            'friendly': '🏭 Firms under R50 million turnover',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'business_firms_under_r50_million_turnover'
            },
        },
        {
            'friendly': '📸 Tourism sector SMEs',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'business_tourism_sector_smes'
            },
        },
        {
            'friendly': '🏦 Bank specific programs',
            'dest': {
                'type': DEST_TYPE_MENU,
                'value': 'bank_specific_programs'
            },
        },
    ]
}

menus['individual'] = {
    'intro': "Hello and welcome to 🤖 Digisist Individual.\nOver here you will be able to link your SASSA account with Digisist in order for you to receive and manage your grants digitally.",
    'options': [
        {
            'friendly': '💁🏻 My Social Grants',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'profile_my_social_grant'
            },
        },
        {
            'friendly': '🏧 All Social Grants',
            'dest': {
                'type': DEST_TYPE_MENU,
                'value': 'all_grants'
            },
        },
        {
            'friendly': '👱 My Profile',
            'dest': {
                'type': DEST_TYPE_MENU,
                'value': 'profile'
            },
        },
    ]
}

menus['all_grants'] = {
    'intro': "Here are the list of all grants you could be able to apply.",
    'options': [
        {
            'friendly': '👶 Child Dependency Grant',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'child_dependency_grant'
            },
        },
        {
            'friendly': '🍼 Child Support Grant',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'child_support_grant'
            },
        },
        {
            'friendly': '♿ Disability Grant',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'disability_grant'
            },
        },
        {
            'friendly': 'Foster Child Grant',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'foster_child_grant'
            },
        },
        {
            'friendly': 'Grant-in-aid',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'grant_in_aid'
            },
        },
        {
            'friendly': '👴🏽 Old Persons Grant',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'old_persons_grant'
            },
        },
        {
            'friendly': '🆘 Social Relief or Distress',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'social_relief_grant'
            },
        },
        {
            'friendly': '🎖️ War Veterans Grant',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'war_veterans_grant'
            },
        },
    ]
}

menus['profile'] = {
    'intro': "{}, you can manage your personal information here. Select an option:",
    'options': [
        {
            'friendly': '👱 Get my Profile Details',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'my_profile_details'
            },
        },
        {
            'friendly': '🗑️ Delete my Profile',
            'dest': {
                'type': DEST_TYPE_MENU,
                'value': 'delete_profile_confirmation'
            },
        },
    ]
}

menus['delete_profile_confirmation'] = {
    'intro': "{}, Are you sure that you want to delete your profile?",
    'options': [
        {
            'friendly': '👍 Yes',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'delete_my_profile'
            },
        },
        {
            'friendly': '🙅‍♀️ No',
            'dest': {
                'type': DEST_TYPE_MENU,
                'value': 'profile'
            },
        },
    ]
}

menus['bank_specific_programs'] = {
    'intro': "Some banks have offered their own programs. Select the bank below to find out more about them:",
    'options': [
        {
            'friendly': 'Standard Bank',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'business_bank_standard_bank'
            },
        },
        {
            'friendly': 'Nedbank',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'business_bank_nedbank'
            },
        },
    ]
}


def get_dest_for_selection(menu, selection):
    #  check for index out of range.. return retry
    index = int(selection) - 1
    return menus[menu]['options'][index]['dest']


def get_menu(menu, user_name):
    # response = ""
    # print("MENU IS " + menu)
    # if menu != 'main':
    #     response = "Heyyy {}, 🤖\n".format(user_name)
    # response += menus[menu]['intro'] + "\n"
    response = menus[menu]['intro'].format(user_name) + "\n\n"

    for i, item in enumerate(menus[menu]['options'], start=1):
        response += "{}) {}\n\n".format(str(i), item['friendly'])

    response += '99) Help\n' \
                '0) Back\n'

    return response


@application.route('/api/v1/coronials/init', methods=['GET', 'POST'])
def get_init():
    payload = request.form
    userId = payload['UserIdentifier']
    print('user init ' + userId)
    starting_menu = 'main'

    try:
        user = get_user_by_user_identifier(userId)
        stack = [starting_menu]
        return build_twilio_collect_from_menu(starting_menu, stack, request)
    except NoResultFound:
        print('Not registered yet...')
        return build_twilio_task_redirect('register')


@application.route('/api/v1/coronials/user/delete', methods=['POST'])
def delete_user_profile():
    payload = request.form
    userId = payload['UserIdentifier']

    try:
        user = get_user_by_user_identifier(userId)
        delete_user(user)
    except NoResultFound:
        return build_twilio_task_redirect('greeting')

    db.session.commit()

    return build_twilio_task_redirect('profile_delete')


@application.route('/api/v1/coronials/greeting', methods=['GET', 'POST'])
def greeting():
    payload = request.form
    userId = payload['UserIdentifier']

    response = "Heyyyyy"

    try:
        user = get_user_by_user_identifier(userId)
        response += " {}, ".format(user.name)
    except NoResultFound:
        response += " and "
        print("he who shall be nameless")

    response += "welcome to Digisist 🤖!"

    return build_say_and_task_redirect(response, 'introduction')


@application.route('/api/v1/menu/global-back', methods=['GET', 'POST'])
def gp_back():
    payload = request.form
    # print("BACK STACK")
    # print(back_menu_stack)

    print("MENU STORE")
    print(back_menu_store)

    try:
        back_menu = back_menu_store[payload['UserIdentifier']]
        return build_twilio_collect_from_menu(back_menu, [back_menu], request)
    except KeyError:
        print('no back menu.. oh well')
        starting_menu = 'main'
        return build_twilio_collect_from_menu(starting_menu, [starting_menu], request)


@application.route('/api/v1/menu/callback', methods=['GET', 'POST'])
def callback_all():
    payload = request.form
    menu_store = json.loads(payload['Memory'])['menu']
    menu_stack = menu_store['stack']

    user_response = get_menu_response(request)
    selection = int(user_response)

    if selection == 0:
        try:
            previous_menu = menu_stack.pop()
            print('PREVIOUS MENU -> ' + previous_menu)
            return build_twilio_collect_from_menu(previous_menu, menu_stack, request)
        except IndexError:
            print('no back menu.. cause stack is popped.. oh well')
            starting_menu = 'main'
            return build_twilio_collect_from_menu(starting_menu, [starting_menu], request)

    if selection == 99:
        # TODO may need to make this a menu..
        return build_twilio_task_redirect('help')

    current_menu = menu_store['current']
    print('CURRENT MENU -> ' + current_menu)
    try:
        dest = get_dest_for_selection(current_menu, selection)
    except IndexError:
        print("Eish, why these guys entering an index out of bounds?")
        return build_twilio_collect_from_menu(current_menu, menu_stack, request)

    back_menu_store[payload['UserIdentifier']] = current_menu

    if dest['type'] == DEST_TYPE_TASK:
        return build_twilio_task_redirect(dest['value'])

    # TODO get name here AKA BOB
    if dest['type'] == DEST_TYPE_MENU:
        menu_stack.append(current_menu)
        # back_menu_stack[payload['UserIdentifier']].append(current_menu)
        return build_twilio_collect_from_menu(dest['value'], menu_stack, request)


def get_menu_response(request):
    payload = request.form
    memory = json.loads(payload['Memory'])
    answers = memory['twilio']['collected_data']['collect_menu_selection']['answers']
    selection = answers['menu_selection']['answer']
    return selection


@application.route('/api/v1/coronials/create-user', methods=['GET', 'POST'])
def create_user_twilio():
    payload = request.form
    userId = payload['UserIdentifier']
    memory = json.loads(payload['Memory'])
    answers = memory['twilio']['collected_data']['register_user']['answers']

    name = answers['name']['answer']
    id_number = answers['id_number']['answer']

    bank = answers['bank_name']['answer']
    bank_acc_no = answers['bank_acc_no']['answer']
    bank_branch_no = answers['bank_branch_code']['answer']

    new_bank = BankAccount(bank=bank, accno=bank_acc_no, branch=bank_branch_no)
    db.session.add(new_bank)

    new_user = User(user_identifier=userId, name=name, id_number=id_number)
    new_user.bankaccounts.append(new_bank)

    db.session.add(new_user)
    db.session.commit()

    # response = "Hello {}, thanks for registering :D".format(name)
    return build_twilio_say(SUCCESSFUL_REGISTRATION_MSG)


def build_twilio_collect_from_menu(menu, stack, incoming_request):
    display_name = None

    remember_payload = {
        'menu': {
            "current": menu,
            "stack": stack
        }
    }

    payload = incoming_request.form
    try:
        display_name = json.loads(payload['Memory'])['username']
    except KeyError:
        print("Didn't find it in the resp - memory wiped :(")

    if display_name is None:
        try:
            userId = payload['UserIdentifier']
            user = get_user_by_user_identifier(userId)
            display_name = user.name
            remember_payload['username'] = display_name
        except NoResultFound:
            print('we got prpbs here')

    menu_response = get_menu(menu, display_name)
    redirect_path = get_full_api_path("/api/v1/menu/callback")

    return jsonify({
        "actions": [
            {
                "collect": {
                    "name": "collect_menu_selection",
                    "questions": [
                        {
                            "question": menu_response,
                            "name": "menu_selection",
                            "type": "Twilio.NUMBER"
                        }
                    ],
                    "on_complete": {
                        "redirect": redirect_path
                    }
                }
            },
            {
                "remember": remember_payload
            },
        ]
    })



def get_full_api_path(path):
    return "{}{}".format(API_BASE_PATH, path)


def build_twilio_api_redirect(path):
    return jsonify({"actions": [{"redirect": get_full_api_path(path)}]})


def build_twilio_task_redirect(task):
    return jsonify({
        "actions": [
            {
                "redirect": "task://{}".format(task)
            }
        ]})


def build_twilio_task_redirect_with_remember_user(task, username):
    return jsonify({
        "actions": [{
            "redirect": "task://{}".format(task)
        },
        {
            "remember": {
                "username": username
            }
        }]
    })


def build_twilio_say(say_text):
    return jsonify({"actions": [{"say": say_text}]})


def build_say_and_task_redirect(say, task):
    return jsonify({
        "actions": [
            {
                "say": say
            },
            {
                "redirect": "task://{}".format(task)
            }
        ]
    })

# print a nice greeting.
def say_hello(username="World"):
    # message = client.messages.create(to="+no", from_="+no", body="Hello there, " + username)
    return '<p>Hello %s!</p>\n' % username


# some bits of text for the page.
header_text = '''
    <html>\n<head> <title>COVID19 Hack</title> </head>\n<body>'''
instructions = '''
    <p><em>Hint</em>: This is a RESTful web service! Append a username
    to the URL (for example: <code>/covid</code>) to say hello to
    someone specific.</p>\n'''
home_link = '<p><a href="/">Back</a></p>\n'
footer_text = '</body>\n</html>'

# add a rule for the index page.
application.add_url_rule('/', 'index', (lambda: header_text +
                                                say_hello() + instructions + footer_text))

# add a rule when the page is accessed with a name appended to the site
# URL.
application.add_url_rule('/<username>', 'hello', (lambda username:
                                                  header_text + say_hello(username) + home_link + footer_text))


def get_user_by_user_identifier(user_identifier):
    return db.session.query(User).filter_by(user_identifier=user_identifier).one()


def delete_user(user):
    db.session.delete(user)


def create_missing_identifier_response(field):
    response = jsonify({
        'message': 'Missing request parameter: "{}"'.format(field)
    })
    return response


def create_database():
    with application.app_context():
        db.create_all()
        insert_seed_data(db)
        db.session.commit()


# run the app.
if __name__ == "__main__":
    # Setting debug to True enables debug output. This line should be
    # removed before deploying a production app.
    application.debug = True
    create_database()
    application.run(port=5001, debug=False)
