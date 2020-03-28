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

# Twilio Dinges make these environment vars
account = "TwilioAccountID"
token = "TwilioAccountToken"
client = Client(account, token)
# End Twilio Dinges


@application.route('/api/v1/webhook/twilio', methods=['POST'])
def twilio_hook():
    # if not request.json or not 'title' in request.json:
    #     abort(400)
    # task = {
    #     'id': tasks[-1]['id'] + 1,
    #     'title': request.json['title'],
    #     'description': request.json.get('description', ""),
    #     'done': False
    # }
    # tasks.append(task)
    payload = request.json
    print(payload)
    return jsonify({'payload': payload}), 201


@application.route('/api/v1/deployer/images', methods=['GET'])
def get_images():
    images = 'Available Images:' + NEW_LINE
    for i in get_images_payload():
        images += i + NEW_LINE

    return build_twilio_say(images)


@application.route('/api/v1/info/daily-users', methods=['GET'])
def get_daily_users():
    android = get_random_number(1000, 100000)
    ios = get_random_number(1000, 100000)
    web = get_random_number(1000, 100000)
    response = "Daily Login Info:\n\nMobile:\nAndroid: " + android + "\niOS: " + ios + "\n\nWeb: " + web

    return build_twilio_say(response)


@application.route('/api/v1/info/support', methods=['GET'])
def get_support():
    response = "Support:\n\n" \
               "Mobile:\n" \
               "BA: Nik Nik\n" \
               "Developer: Rossi\n\n" \
               "Website:\n" \
               "BA: Nik Naik\n" \
               "Developer: Wald"

    return build_twilio_say(response)


@application.route('/api/v1/info/abilities', methods=['GET'])
def get_abilities():
    response = "Try the following commands: \r\nGet deployment images, \r\nGet deployment labels, \r\nInstant Deployments, " \
               "\r\nScheduled Deployments, \r\nPending approvals, \r\nSupport Roster, \r\nDaily Users, " \
               "\r\nMonthly Users, \r\nHow many login's succeeded today, \r\nFailure rate, \r\nScreen views. " \
               "\r\n\r\nTry this in Google assistant, WhatsApp or Slack."

    return build_twilio_say(response)


@application.route('/api/v1/info/login-failures', methods=['GET'])
def get_login_failures():
    app = get_random_decimal(90, 100, 2)
    web = get_random_decimal(90, 100, 2)
    response = "App login success: " + app + "% \r\nWeb login success: " + web + "%"

    return build_twilio_say(response)


@application.route('/api/v1/info/image-failures', methods=['GET', 'POST'])
def get_image_failures():
    payload = request.form
    memory = json.loads(payload['Memory'])
    answers = memory['twilio']['collected_data']['collect_images']['answers']
    image = answers['image_failure_rates']['answer']
    failure_rate = get_random_decimal(0, 10, 2)
    response = "There is a " + failure_rate + "% failure rate on {}".format(image)

    return build_twilio_say(response)


@application.route('/api/v1/info/most-used', methods=['GET'])
def get_most_used():
    vitality_landing = get_random_number(100000, 1000000)
    index = get_random_number(100000, 1000000)
    response = "Mobile: landing_page " + vitality_landing + " views \r\nWeb: /index.html " + index + " views"

    return build_twilio_say(response)


@application.route('/api/v1/info/monthly-users', methods=['GET'])
def get_monthly_users():
    android = get_random_number(1000, 100000)
    ios = get_random_number(1000, 100000)
    web = get_random_number(1000, 100000)
    response = "Monthly Login Info:\n\nMobile:\nAndroid: " + android + "\niOS: " + ios + "\n\nWeb: " + web

    return build_twilio_say(response)


@application.route('/api/v1/whatsapp/deployer/images', methods=['GET'])
def get_wa_images():
    images = 'Available Images:' + NEW_LINE
    for i in get_images_payload():
        images += i + NEW_LINE

    return build_twilio_say(images)


# @Richard TODO User management
# Put your stuff here

# User management
@application.route('/api/v1/user/<string:user_identifier>', methods=['GET'])
def get_user_by_identifier(user_identifier):
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


@application.route('/api/v1/coronials/hello', methods=['GET', 'POST'])
def get_hello():
    response = "Hello, this is the backend on AWS saying WORLD"
    return build_twilio_say(response)


@application.route('/api/v1/coronials/age', methods=['GET', 'POST'])
def get_age():
    print('methods')
    print(request.method['GET'])
    form = request.form
    age = int(form['Field_user_age_Value'])
    age += age

    response = "Double your age is {}".format(age)

    return build_twilio_say(response)

@application.route('/api/v1/deployer/labels', methods=['GET', 'POST'])
def get_labels():
    field = 'CurrentInput'
    if field in request.form:
        images = 'The following labels are available for "' + request.form[field] + '"' + NEW_LINE
    else:
        images = 'Available labels ' + NEW_LINE

    for i in get_labels_payload():
        images += i + NEW_LINE

    return build_twilio_say(images)


@application.route('/api/v1/deployer/deploy', methods=['GET', 'POST'])
def do_deploy():
    payload = request.form
    memory = json.loads(payload['Memory'])
    answers = memory['twilio']['collected_data']['deploy_questions']['answers']
    deployment_image = answers['deployment_images']['answer']
    deployment_label = answers['deployment_labels']['answer']

    result = "Deploying '{}' on '{}'".format(deployment_label, deployment_image)
    print(result)

    return build_twilio_say(result)


@application.route('/api/v1/deployer/deploy-schedule', methods=['GET', 'POST'])
def do_deploy_schedule():
    payload = request.form
    memory = json.loads(payload['Memory'])
    answers = memory['twilio']['collected_data']['deploy_questions']['answers']
    deployment_image = answers['deployment_images']['answer']
    deployment_label = answers['deployment_labels']['answer']
    deployment_time = answers['deployment_time']['answer']

    result = "Deploying '{}' on '{}' @ {}".format(deployment_label, deployment_image, deployment_time)

    if deployment_time not in ['09:00',
                               '09h00',
                               '9am',
                               '12:00',
                               '12h00',
                               '12pm',
                               '16:00',
                               '16h00',
                               '4pm']:

        result = "Please deploy during the allotted time slots!\n\n" \
                 "09h00 until 09h30\n" \
                 "12h00 until 12h30\n" \
                 "16h00 until 16h30"

    return build_twilio_say(result)


def send_sms(body):
    if SETTINGS_ENABLE_SMS:
        sms = client.messages.create(to="<to-nohere>", from_="<from-nohere>", body=body)
    else:
        print(">>>>SMS<<<<\n{}\n>>>>>SMS<<<<<<".format(body))


def build_twilio_task_redirect(task):
    return jsonify({"actions": [{"redirect": "task://{}".format(task)}]})


def build_twilio_say(say_text):
    return jsonify({"actions": [{"say": say_text}]})

# hard coded dinges


def get_images_payload():
    payload = [
        'image1',
        'image2',
        'image3',
    ]
    return payload


def get_labels_payload():
    payload = [
        'label1',
        'label2',
        'label3',
    ]
    return payload


def get_random_number(min, max):
    return str(random.randint(min, max))


def get_random_decimal(min, max, decimals):
    return str(round(random.uniform(min, max), decimals))


@application.route('/api/v1/test', methods=['GET'])
def get_test():
    return jsonify({'tasks': 'pew'})


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
