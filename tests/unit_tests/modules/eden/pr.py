# -*- coding: utf-8 -*-
#
# PR Unit Tests
#
# To run this script use:
# python web2py.py -S eden -M -R applications/eden/tests/unit_tests/modules/eden/pr.py
#
import unittest
import datetime

from gluon import current

# =============================================================================
class PRTests(unittest.TestCase):
    """ PR Tests """

    def setUp(self):
        pass

    def testGetRealmUsers(self):

        try:

            auth.s3_impersonate("admin@example.com")
            admin_id = auth.user.id
            admin_pe_id = auth.s3_user_pe_id(admin_id)
            auth.s3_impersonate("normaluser@example.com")
            user_id = auth.user.id
            user_pe_id = auth.s3_user_pe_id(user_id)
            auth.s3_impersonate(None)

            organisations = s3db.pr_get_entities(types="org_organisation", as_list=True, represent=False)
            org1 = organisations[0]
            org2 = organisations[1]

            users = s3db.pr_realm_users(org1)
            self.assertEqual(users, Storage())

            users = s3db.pr_realm_users(org2)
            self.assertEqual(users, Storage())

            s3db.pr_add_affiliation(org1, admin_pe_id, role="Volunteer", role_type=9)
            s3db.pr_add_affiliation(org2, user_pe_id, role="Staff")

            users = s3db.pr_realm_users(org1)
            self.assertFalse(user_id in users)
            self.assertFalse(admin_id in users)

            users = s3db.pr_realm_users(org2)
            self.assertTrue(user_id in users)
            self.assertFalse(admin_id in users)

            users = s3db.pr_realm_users([org1, org2])
            self.assertTrue(user_id in users)
            self.assertFalse(admin_id in users)

            users = s3db.pr_realm_users(org1, roles="Volunteer")
            self.assertFalse(user_id in users)
            self.assertTrue(admin_id in users)

            users = s3db.pr_realm_users(org2, roles="Volunteer")
            self.assertFalse(user_id in users)
            self.assertFalse(admin_id in users)

            users = s3db.pr_realm_users([org1, org2], roles="Volunteer")
            self.assertFalse(user_id in users)
            self.assertTrue(admin_id in users)

            users = s3db.pr_realm_users(org1, roles="Staff")
            self.assertFalse(user_id in users)
            self.assertFalse(admin_id in users)

            users = s3db.pr_realm_users(org2, roles="Staff")
            self.assertTrue(user_id in users)
            self.assertFalse(admin_id in users)

            users = s3db.pr_realm_users([org1, org2], roles="Staff")
            self.assertTrue(user_id in users)
            self.assertFalse(admin_id in users)

            users = s3db.pr_realm_users([org1, org2], roles=["Staff", "Volunteer"])
            self.assertTrue(user_id in users)
            self.assertTrue(admin_id in users)

            users = s3db.pr_realm_users([org1, org2], role_types=1)
            self.assertTrue(user_id in users)
            self.assertFalse(admin_id in users)

            users = s3db.pr_realm_users([org1, org2], role_types=9)
            self.assertFalse(user_id in users)
            self.assertTrue(admin_id in users)

            users = s3db.pr_realm_users([org1, org2], role_types=None)
            self.assertTrue(user_id in users)
            self.assertTrue(admin_id in users)

            s3db.pr_remove_affiliation(org2, user_pe_id, role="Staff")
            users = s3db.pr_realm_users([org1, org2], role_types=None)
            self.assertFalse(user_id in users)
            self.assertTrue(admin_id in users)

            # None as realm should give a list of all current users
            table = auth.settings.table_user
            query = (table.deleted != True)
            rows = db(query).select(table.id)
            all_users = [row.id for row in rows]
            users = s3db.pr_realm_users(None)
            self.assertTrue(all([u in users for u in all_users]))

        finally:
            db.rollback()

# =============================================================================
class PersonDeduplicateTests(unittest.TestCase):
    """ PR Tests """

    def setUp(self):

        ptable = s3db.pr_person
        ctable = s3db.pr_contact

        person1 = Storage(first_name = "Test",
                          last_name = "UserDEDUP",
                          initials = "TU",
                          date_of_birth = datetime.date(1974, 4, 13))
        person1_id = ptable.insert(**person1)
        person1.update(id=person1_id)
        s3mgr.model.update_super(ptable, person1)

        self.person1_id = person1_id
        self.pe1_id = s3db.pr_get_pe_id(ptable, person1_id)

        person2 = Storage(first_name = "Test",
                          last_name = "UserDEDUP",
                          initials = "OU",
                          date_of_birth = datetime.date(1974, 4, 23))
        person2_id = ptable.insert(**person2)
        person2.update(id=person2_id)
        s3mgr.model.update_super(ptable, person2)

        self.person2_id = person2_id
        self.pe2_id = s3db.pr_get_pe_id(ptable, person2_id)

    def testHook(self):

        deduplicate = s3mgr.model.get_config("pr_person", "deduplicate")
        self.assertNotEqual(deduplicate, None)
        self.assertTrue(callable(deduplicate))

    def testMatchNames(self):

        deduplicate = s3mgr.model.get_config("pr_person", "deduplicate")

        # Test Match
        person = Storage(first_name = "Test",
                         last_name = "UserDEDUP")
        item = self.import_item(person)
        deduplicate(item)
        self.assertEqual(item.id, self.person1_id)
        self.assertEqual(item.method, s3base.S3ImportItem.METHOD.UPDATE)

        # Test Mismatch
        person = Storage(first_name = "Other",
                         last_name = "UserDEDUP")
        item = self.import_item(person)
        deduplicate(item)
        self.assertNotEqual(item.id, self.person1_id)
        self.assertNotEqual(item.id, self.person2_id)

    def testMatchEmail(self):

        deduplicate = s3mgr.model.get_config("pr_person", "deduplicate")

        # Test without contact records in the DB

        # Test Match
        person = Storage(first_name = "Test",
                         last_name = "UserDEDUP")
        item = self.import_item(person, email="testuser@example.com")
        deduplicate(item)
        self.assertEqual(item.id, self.person1_id)
        self.assertEqual(item.method, s3base.S3ImportItem.METHOD.UPDATE)

        # Test Mismatch
        person = Storage(first_name = "Other",
                         last_name = "UserDEDUP")
        item = self.import_item(person, email="testuser@example.com")
        deduplicate(item)
        self.assertNotEqual(item.id, self.person1_id)
        self.assertNotEqual(item.id, self.person2_id)

        # Insert contact records into the DB
        ctable = s3db.pr_contact
        email = Storage(pe_id = self.pe1_id,
                        contact_method = "EMAIL",
                        value = "testuser@example.com")
        ctable.insert(**email)
        email = Storage(pe_id = self.pe2_id,
                        contact_method = "EMAIL",
                        value = "otheruser@example.org")
        ctable.insert(**email)

        # Test with contact records in the DB

        # Test Match - same names, same email
        person = Storage(first_name = "Test",
                         last_name = "UserDEDUP")
        item = self.import_item(person, email="testuser@example.com")
        deduplicate(item)
        self.assertEqual(item.id, self.person1_id)
        self.assertEqual(item.method, s3base.S3ImportItem.METHOD.UPDATE)

        # Test Match - same names, different email
        person = Storage(first_name = "Test",
                         last_name = "UserDEDUP")
        item = self.import_item(person, email="otheremail@example.com")
        deduplicate(item)
        self.assertEqual(item.id, self.person1_id)
        self.assertEqual(item.method, s3base.S3ImportItem.METHOD.UPDATE)

        # Test Match - same names, same email, but different record
        person = Storage(first_name = "Test",
                         last_name = "UserDEDUP")
        item = self.import_item(person, email="otheruser@example.org")
        deduplicate(item)
        self.assertEqual(item.id, self.person2_id)
        self.assertEqual(item.method, s3base.S3ImportItem.METHOD.UPDATE)

        # Test Mismatch - First names different
        person = Storage(first_name = "Other",
                         last_name = "UserDEDUP")
        item = self.import_item(person, email="testuser@example.com")
        deduplicate(item)
        self.assertNotEqual(item.id, self.person1_id)
        self.assertNotEqual(item.id, self.person2_id)

    def testMatchInitials(self):

        deduplicate = s3mgr.model.get_config("pr_person", "deduplicate")

        # Insert contact records into the DB
        ctable = s3db.pr_contact
        email = Storage(pe_id = self.pe1_id,
                        contact_method = "EMAIL",
                        value = "testuser@example.com")
        ctable.insert(**email)
        email = Storage(pe_id = self.pe2_id,
                        contact_method = "EMAIL",
                        value = "otheruser@example.org")
        ctable.insert(**email)

        # Test Match - same initials
        person = Storage(initials="TU")
        item = self.import_item(person)
        deduplicate(item)
        self.assertEqual(item.id, self.person1_id)
        self.assertEqual(item.method, s3base.S3ImportItem.METHOD.UPDATE)

        # Test Match - same names, different initials
        person = Storage(first_name="Test",
                         last_name="UserDEDUP",
                         initials="OU")
        item = self.import_item(person)
        deduplicate(item)
        self.assertEqual(item.id, self.person2_id)
        self.assertEqual(item.method, s3base.S3ImportItem.METHOD.UPDATE)

        # Test Match - same names, different initials, and email
        person = Storage(first_name="Test",
                         last_name="UserDEDUP",
                         initials="OU")
        item = self.import_item(person, email="testuser@example.org")
        deduplicate(item)
        self.assertEqual(item.id, self.person2_id)
        self.assertEqual(item.method, s3base.S3ImportItem.METHOD.UPDATE)

        # Test Match - same initials
        person = Storage(initials="OU")
        item = self.import_item(person)
        deduplicate(item)
        self.assertEqual(item.id, self.person2_id)
        self.assertEqual(item.method, s3base.S3ImportItem.METHOD.UPDATE)

        # Test Match - same initials, same email
        person = Storage(initials="TU")
        item = self.import_item(person, email="testuser@example.com")
        deduplicate(item)
        self.assertEqual(item.id, self.person1_id)
        self.assertEqual(item.method, s3base.S3ImportItem.METHOD.UPDATE)

    def testMatchDOB(self):

        deduplicate = s3mgr.model.get_config("pr_person", "deduplicate")

        # Insert contact records into the DB
        ctable = s3db.pr_contact
        email = Storage(pe_id = self.pe1_id,
                        contact_method = "EMAIL",
                        value = "testuser@example.com")
        ctable.insert(**email)
        email = Storage(pe_id = self.pe2_id,
                        contact_method = "EMAIL",
                        value = "otheruser@example.org")
        ctable.insert(**email)

        # Test Match - same initials, different email, same DOB
        person = Storage(initials="TU",
                         date_of_birth=datetime.date(1974, 4, 13))
        item = self.import_item(person, email="otheremail@example.com")
        deduplicate(item)
        self.assertEqual(item.id, self.person1_id)

        # Test MisMatch - same initials, different email, different DOB
        person = Storage(initials="TU",
                         date_of_birth=datetime.date(1975, 6, 17))
        item = self.import_item(person, email="otheremail@example.com")
        deduplicate(item)
        self.assertNotEqual(item.id, self.person1_id)
        self.assertNotEqual(item.id, self.person2_id)

    def import_item(self, person, email=None, sms=None):
        """ Construct a fake import item """

        def item(tablename, data):
            return Storage(id = None,
                           method = None,
                           tablename = tablename,
                           data = data,
                           components = [],
                           METHOD = s3base.S3ImportItem.METHOD)
        import_item = item("pr_person", person)
        if email:
            import_item.components.append(item("pr_contact",
                                Storage(contact_method = "EMAIL",
                                        value = email)))
        if sms:
            import_item.components.append(item("pr_contact",
                                Storage(contact_method = "SMS",
                                        value = sms)))
        return import_item

    def tearDown(self):

        db.rollback()
        self.pe_id = None
        self.person_id = None

# =============================================================================
def run_suite(*test_classes):
    """ Run the test suite """

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    if suite is not None:
        unittest.TextTestRunner().run(suite)
    return

if __name__ == "__main__":

    run_suite(
        PRTests,
        PersonDeduplicateTests,
    )

# END ========================================================================
