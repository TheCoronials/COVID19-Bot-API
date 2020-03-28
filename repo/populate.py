from repo.database_setup import User, BankAccount


def insert_seed_data(db):
    test_user_1 = User(user_identifier='+27720000000', name='Richard', id_number='9201100000000')

    bank1 = BankAccount(bank='Nedbank', accno='123456789', branch='123456')

    db.session.add(test_user_1)
    db.session.add(bank1)
    db.session.commit()
