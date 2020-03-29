import requests
from flask import Flask, request, abort, app, jsonify, json
from sqlalchemy.orm.exc import NoResultFound
from twilio.rest import Client
from flask_sqlalchemy import SQLAlchemy
from repo.database_setup import User, BankAccount, Base
import random

# EB looks for an 'application' callable by default.
from repo.populate import insert_seed_data

application = Flask(__name__)

application.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///coronials-collection.db'
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
application.config['SQLALCHEMY_ECHO'] = True

db = SQLAlchemy(application)

SETTINGS_ENABLE_SMS = True
NEW_LINE = '\r\n'
API_BASE_PATH = 'https://c640a319.ngrok.io'
DEST_TYPE_MENU = "MENU"
DEST_TYPE_TASK = "TASK"

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


menus = {}

### TEAM INFO around how to use menu system
# -> Main Menu is defined at the root as menus['main'] see below
# -> To add a new menu, create menus['menu-name'] = {} use menus['main'] or menus['business'] as example
# -> To link to a menu use DEST_TYPE_MENU type and set value to menu as defined here. EG menus['business']
# -> To link to a task defined in twilio, use DEST_TYPE_TASK type and set value to task as defined in twilio
# -> remember to create call-back function..

menus['main'] = {
    'intro': "I'm TheCoronials bot for COVID-19 Hackathon!",
    'options': [
        {
            'friendly': 'My Profile',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'profile_menu'
            },
        },
        {
            'friendly': 'Social Grants',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'profile_menu'
            },
        },
        {
            'friendly': 'Business Menu',
            'dest': {
                'type': DEST_TYPE_MENU,
                'value': 'business'
            },
        },
    ]
}

menus['business'] = {
    'intro': "This is the Business Menu",
    'options': [
        {
            'friendly': 'Business Loans',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'business_loans'
            },
        },
        {
            'friendly': 'Donation school feeding program',
            'dest': {
                'type': DEST_TYPE_TASK,
                'value': 'donation_school_feeding_program'
            },
        },
    ]
}


def get_dest_for_selection(menu, selection):
    index = int(selection) - 1
    return menus[menu]['options'][index]['dest']


def get_menu(menu, user_name):
    response = "Heyyy {},\n".format(user_name)
    response += menus[menu]['intro'] + "\n"
    for i, item in enumerate(menus[menu]['options'], start=1):
        response += "{}) {}\n".format(str(i), item['friendly'])

    response += '\nh) Help\n' \
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
        return build_twilio_collect_from_menu(starting_menu, stack, user.name)
    except NoResultFound:
        print('Not registered yet...')
        return build_twilio_task_redirect('register')


@application.route('/api/v1/menu/global-back', methods=['GET', 'POST'])
def gp_back():
    response = "Hmmm.. so you wanna go back? Still need to think about that.."
    return build_twilio_say(response)


@application.route('/api/v1/menu/callback', methods=['GET', 'POST'])
def callback_all():
    payload = request.form
    menu_store = json.loads(payload['Memory'])['menu']

    current_menu = menu_store['current']
    menu_stack = menu_store['stack']
    # previous_menu = menu_store['stack'].pop()

    print('CURRENT MENU -> ' + current_menu)

    # use this for text later
    user_response = get_menu_response(request)

    #
    # if str(user_response).lower() == 'b':
    #     print('about to go here ' + previous_menu)

    # TODO may break if they don't put 1 as answer.. handle..
    selection = int(user_response)
    if selection == 0:
        previous_menu = menu_stack.pop()
        print('PREVIOUS MENU -> ' + previous_menu)
        return build_twilio_collect_from_menu(previous_menu, menu_stack, 'BOB')

    dest = get_dest_for_selection(current_menu, selection)

    if dest['type'] == DEST_TYPE_TASK:
        return build_twilio_task_redirect(dest['value'])

    # TODO get name here AKA BOB
    if dest['type'] == DEST_TYPE_MENU:
        menu_stack.append(current_menu)
        return build_twilio_collect_from_menu(dest['value'], menu_stack, 'BOB')


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
    return build_twilio_task_redirect('greeting')

def build_twilio_collect_from_menu(menu, stack, user_name):
    menu_response = get_menu(menu, user_name)
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
                            "type": "Twilio.ALPHANUMERIC"
                        }
                    ],
                    "on_complete": {
                        "redirect": redirect_path
                    }
                }
            },
            {
                "remember": {
                    "menu": {
                        "current": menu,
                        "stack": stack
                    },
                }
            },
        ]
    })



def get_full_api_path(path):
    return "{}{}".format(API_BASE_PATH, path)


def build_twilio_api_redirect(path):
    return jsonify({"actions": [{"redirect": get_full_api_path(path)}]})


def build_twilio_task_redirect(task):
    return jsonify({
        "actions": [{
            "redirect": "task://{}".format(task)
        }]
    })


def build_twilio_say(say_text):
    return jsonify({"actions": [{"say": say_text}]})


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
