import mock
import unittest
import json
try:
    # Python 3.3 >
    from unittest.mock import MagicMock  # noqa: F401
except ImportError:
    from mock import MagicMock  # noqa: F401


import sync2jira.upstream as u


PATH = 'sync2jira.upstream.'


class TestUpstream(unittest.TestCase):
    """
    This class tests the upstream.py file under sync2jira
    """
    def setUp(self):
        self.mock_config = {
            'sync2jira': {
                'map': {
                    'github': {
                        'org/repo': {},
                    },
                    'pagure': {
                        'org/repo': {},
                    },
                },
                'jira': {
                    # Nothing, really..
                },
                'filters': {
                    'github':
                        {'org/repo': {'filter1': 'filter1', 'labels': 'custom_tag'}},
                    'pagure':
                        {'org/repo': {'filter1': 'filter1', 'tags': ['custom_tag']}},
                },
                'github_token': 'mock_token'
            },
        }
        # Mock Pagure Message
        self.mock_pagure_message = {
            'msg': {
                'project': {
                    'name': 'org/repo'
                },
                'issue': {
                    'filter1': 'filter1',
                    'tags': ['custom_tag'],
                    'comments': [],
                    'assignee': 'mock_assignee'
                },
                'tags': ['new_tag'],
                'comment': 'new_comment',
                'status': 'temp'
            },
            'topic': 'io.pagure.prod.pagure.issue.drop',
        }

        # Mock Github Comment
        self.mock_github_comment = MagicMock()
        self.mock_github_comment.user.name = 'mock_username'
        self.mock_github_comment.user.login = 'mock_user_login'
        self.mock_github_comment.body = 'mock_body'
        self.mock_github_comment.id = 'mock_id'
        self.mock_github_comment.created_at = 'mock_created_at'

        # Mock Github Message
        self.mock_github_message = {
            'msg': {
                'repository': {
                    'owner': {
                        'login': 'org'
                    },
                    'name': 'repo'
                },
                'issue': {
                    'filter1': 'filter1',
                    'labels': [{'name': 'custom_tag'}],
                    'comments': ['some_comments!'],
                    'number': 'mock_number',
                    'user': {
                        'login': 'mock_login'
                    },
                    'assignees': [{'login': 'mock_login'}],
                    'milestone': {
                        'title': 'mock_milestone'
                    }
                }
            }
        }

        # Mock github issue
        self.mock_github_issue = MagicMock()
        self.mock_github_issue.get_comments.return_value = [self.mock_github_comment]

        # Mock Github Issue Raw
        self.mock_github_issue_raw = {
            'comments': ['some comment'],
            'number': '1234',
            'user': {
                'login': 'mock_login'
            },
            'assignees': [{'login': 'mock_assignee_login'}],
            'labels': [{'name': 'some_label'}],
            'milestone': {
                'title': 'mock_milestone'
            }
        }

        # Mock Github Reporter
        self.mock_github_person = MagicMock()
        self.mock_github_person.name = 'mock_name'

        # Mock Github Repo
        self.mock_github_repo = MagicMock()
        self.mock_github_repo.get_issue.return_value = self.mock_github_issue

        # Mock Github Client
        self.mock_github_client = MagicMock()
        self.mock_github_client.get_repo.return_value = self.mock_github_repo
        self.mock_github_client.get_user.return_value = self.mock_github_person

    @mock.patch('sync2jira.intermediary.Issue.from_github')
    @mock.patch(PATH + 'Github')
    @mock.patch(PATH + '_get_all_github_issues')
    def test_github_issues(self,
                           mock_get_all_github_issues,
                           mock_github,
                           mock_issue_from_github):
        """
        This function tests 'github_issues' function
        """
        # Set up return values
        mock_github.return_value = self.mock_github_client
        mock_get_all_github_issues.return_value = [self.mock_github_issue_raw]
        mock_issue_from_github.return_value = 'Successful Call!'

        # Call the function
        response = list(u.github_issues(
            upstream='org/repo',
            config=self.mock_config
        ))

        # Assert that calls were made correctly
        try:
            mock_get_all_github_issues.assert_called_with(
                'https://api.github.com/repos/org/repo/issues?labels=custom_tag&filter1=filter1',
                {'Authorization': 'token mock_token'}
            )
        except AssertionError:
            mock_get_all_github_issues.assert_called_with(
                'https://api.github.com/repos/org/repo/issues?filter1=filter1&labels=custom_tag',
                {'Authorization': 'token mock_token'}
            )
        self.mock_github_client.get_user.assert_any_call('mock_login')
        self.mock_github_client.get_user.assert_any_call('mock_assignee_login')
        mock_issue_from_github.assert_called_with(
            'org/repo',
            {'labels': ['some_label'], 'number': '1234', 'comments': [
                {'body': 'mock_body', 'name': 'mock_user_login', 'author': 'mock_username', 'changed': None,
                 'date_created': 'mock_created_at', 'id': 'mock_id'}], 'assignees': [{'fullname': 'mock_name'}],
             'user': {'login': 'mock_login', 'fullname': 'mock_name'}, 'milestone': 'mock_milestone'},
            self.mock_config
        )
        self.mock_github_client.get_repo.assert_called_with('org/repo')
        self.mock_github_repo.get_issue.assert_called_with(number='1234')
        self.mock_github_issue.get_comments.assert_any_call()
        self.assertEqual(response[0], 'Successful Call!')

    @mock.patch('sync2jira.intermediary.Issue.from_github')
    @mock.patch(PATH + 'Github')
    @mock.patch(PATH + '_get_all_github_issues')
    def test_github_issues_no_token(self,
                                    mock_get_all_github_issues,
                                    mock_github,
                                    mock_issue_from_github):
        """
        This function tests 'github_issues' function where we have no github token
        and no comments
        """
        # Set up return values
        self.mock_config['sync2jira']['github_token'] = None
        self.mock_github_issue_raw['comments'] = 0
        mock_github.return_value = self.mock_github_client
        mock_get_all_github_issues.return_value = [self.mock_github_issue_raw]
        mock_issue_from_github.return_value = 'Successful Call!'

        # Call the function
        response = list(u.github_issues(
            upstream='org/repo',
            config=self.mock_config
        ))

        # Assert that calls were made correctly
        try:
            mock_get_all_github_issues.assert_called_with(
                'https://api.github.com/repos/org/repo/issues?labels=custom_tag&filter1=filter1',
                {}
            )
        except AssertionError:
            mock_get_all_github_issues.assert_called_with(
                'https://api.github.com/repos/org/repo/issues?filter1=filter1&labels=custom_tag',
                {}
            )
        self.mock_github_client.get_user.assert_any_call('mock_login')
        self.mock_github_client.get_user.assert_any_call('mock_assignee_login')
        mock_issue_from_github.assert_called_with(
            'org/repo',
            {'labels': ['some_label'], 'number': '1234', 'comments': [], 'assignees': [{'fullname': 'mock_name'}],
             'user': {'login': 'mock_login', 'fullname': 'mock_name'}, 'milestone': 'mock_milestone'},
            self.mock_config
        )
        self.assertEqual(response[0], 'Successful Call!')
        self.mock_github_client.get_repo.assert_not_called()
        self.mock_github_repo.get_issue.assert_not_called()
        self.mock_github_issue.get_comments.assert_not_called()

    @mock.patch('sync2jira.intermediary.Issue.from_pagure')
    @mock.patch(PATH + 'requests')
    def test_pagure_issues_error(self,
                                 mock_requests,
                                 mock_issue_from_pagure):
        """
        This function tests 'pagure_issues' function where we get an IOError
        """
        # Set up return values
        get_return = MagicMock()
        get_return.__bool__ = mock.Mock(return_value=False)
        get_return.__nonzero__ = get_return.__bool__
        get_return.json.side_effect = Exception()
        get_return.text.return_value = {
            'issues': [
                {'assignee': 'mock_assignee'}
            ]

        }
        mock_requests.get.return_value = get_return

        # Call the function
        with self.assertRaises(IOError):
            list(u.pagure_issues(
                upstream='org/repo',
                config=self.mock_config
            ))

        # Assert everything was called correctly
        mock_requests.get.assert_called_with(
            'https://pagure.io/api/0/org/repo/issues',
            params={'filter1': 'filter1', 'tags': ['custom_tag']}
        )
        mock_issue_from_pagure.assert_not_called()

    @mock.patch('sync2jira.intermediary.Issue.from_pagure')
    @mock.patch(PATH + 'requests')
    def test_pagure_issues(self,
                           mock_requests,
                           mock_issue_from_pagure):
        """
        This function tests 'pagure_issues' function
        """
        # Set up return values
        get_return = MagicMock()
        get_return.json.return_value = {
            'issues': [
                {'assignee': 'mock_assignee'}
            ]

        }
        get_return.request.url = 'mock_url'
        mock_requests.get.return_value = get_return
        mock_issue_from_pagure.return_value = 'Successful Call!'

        # Call the function
        response = list(u.pagure_issues(
            upstream='org/repo',
            config=self.mock_config
        ))

        # Assert everything was called correctly
        self.assertEqual(response[0], 'Successful Call!')
        mock_requests.get.assert_called_with(
            'https://pagure.io/api/0/org/repo/issues',
            params={'filter1': 'filter1', 'tags': ['custom_tag']}
        )
        mock_issue_from_pagure.assert_called_with(
            'org/repo',
            {'assignee': ['mock_assignee']},
            self.mock_config
        )

    @mock.patch('sync2jira.intermediary.Issue.from_pagure')
    def test_handle_pagure_message_not_in_mapped(self,
                                                 mock_issue_from_pagure):
        """
        This function tests 'handle_pagure_message' where upstream is not in mapped repo
        """
        # Set up return values
        self.mock_pagure_message['msg']['project']['name'] = 'bad_repo'
        # Call the function
        response = u.handle_pagure_message(
            msg=self.mock_pagure_message,
            config=self.mock_config
        )

        # Assert all calls made correctly
        self.assertEqual(None, response)
        mock_issue_from_pagure.assert_not_called()

    @mock.patch('sync2jira.intermediary.Issue.from_pagure')
    def test_handle_pagure_message_bad_filter(self,
                                              mock_issue_from_pagure):
        """
        This function tests 'handle_pagure_message' where comparing the actual vs. filter does not equate
        """
        # Set up return values
        self.mock_pagure_message['msg']['issue']['filter1'] = 'filter2'

        # Call function
        response = u.handle_pagure_message(
            msg=self.mock_pagure_message,
            config=self.mock_config)

        # Assert that calls were made correctly
        mock_issue_from_pagure.assert_not_called()
        self.assertEqual(None, response)

    @mock.patch('sync2jira.intermediary.Issue.from_pagure')
    def test_handle_pagure_message_bad_tag(self,
                                           mock_issue_from_pagure):
        """
        This function tests 'handle_pagure_message' where the tags do not match
        """
        # Set up return values
        self.mock_pagure_message['msg']['issue']['tags'] = ['bad_tags']

        # Call function
        response = u.handle_pagure_message(
            msg=self.mock_pagure_message,
            config=self.mock_config)

        # Assert that calls were made correctly
        mock_issue_from_pagure.assert_not_called()
        self.assertEqual(None, response)

    @mock.patch('sync2jira.intermediary.Issue.from_pagure')
    def test_handle_pagure_message_successful(self,
                                              mock_issue_from_pagure):
        """
        This function tests 'handle_pagure_message' where everything goes smoothly
        and we test edge cases!
        """
        # Set up return values
        mock_issue_from_pagure.return_value = "Successful Call!"

        # Call the function
        response = u.handle_pagure_message(
            msg=self.mock_pagure_message,
            config=self.mock_config
        )

        # Assert that calls were made correctly
        mock_issue_from_pagure.assert_called_with(
            'org/repo',
            {'status': 'Dropped', 'assignee': ['mock_assignee'], 'filter1': 'filter1', 'comments': ['new_comment'],
             'tags': ['custom_tag', 'new_tag']},
            self.mock_config
        )
        self.assertEqual(response, 'Successful Call!')

    @mock.patch(PATH + 'Github')
    @mock.patch('sync2jira.intermediary.Issue.from_github')
    def test_handle_github_message_not_in_mapped(self,
                                                 mock_issue_from_github,
                                                 mock_github):
        """
        This function tests 'handle_github_message' where upstream is not in mapped repos
        """
        # Set up return values
        self.mock_github_message['msg']['repository']['owner']['login'] = 'bad_owner'

        # Call the function
        response = u.handle_github_message(
            msg=self.mock_github_message,
            config=self.mock_config
        )

        # Assert that all calls were made correctly
        mock_issue_from_github.assert_not_called()
        mock_github.assert_not_called()
        self.assertEqual(None, response)

    @mock.patch(PATH + 'Github')
    @mock.patch('sync2jira.intermediary.Issue.from_github')
    def test_handle_github_message_pull_request(self,
                                                mock_issue_from_github,
                                                mock_github):
        """
        This function tests 'handle_github_message' the issue is a pull request comment
        """
        # Set up return values
        self.mock_github_message['msg']['issue'] = {'pull_request': 'test'}

        # Call the function
        response = u.handle_github_message(
            msg=self.mock_github_message,
            config=self.mock_config
        )

        # Assert that all calls were made correctly
        mock_issue_from_github.assert_not_called()
        mock_github.assert_not_called()
        self.assertEqual(None, response)

    @mock.patch('sync2jira.intermediary.Issue.from_github')
    def test_handle_github_message_bad_filter(self,
                                              mock_issue_from_github):
        """
        This function tests 'handle_github_message' where comparing the actual vs. filter does not equate
        """
        # Set up return values
        self.mock_github_message['msg']['issue']['filter1'] = 'filter2'

        # Call function
        response = u.handle_github_message(
            msg=self.mock_github_message,
            config=self.mock_config
        )
        # Assert that calls were made correctly
        mock_issue_from_github.assert_not_called()
        self.assertEqual(None, response)

    @mock.patch('sync2jira.intermediary.Issue.from_github')
    def test_handle_github_message_bad_label(self,
                                             mock_issue_from_github):
        """
        This function tests 'handle_github_message' where comparing the actual vs. filter does not equate
        """
        # Set up return values
        self.mock_github_message['msg']['issue']['labels'] = [{'name': 'bad_label'}]

        # Call function
        response = u.handle_github_message(
            msg=self.mock_github_message,
            config=self.mock_config
        )
        # Assert that calls were made correctly
        mock_issue_from_github.assert_not_called()
        self.assertEqual(None, response)

    @mock.patch(PATH + 'Github')
    @mock.patch('sync2jira.intermediary.Issue.from_github')
    def test_handle_github_message_no_comments(self,
                                              mock_issue_from_github,
                                              mock_github):
        """
        This function tests 'handle_github_message' where we have no comments
        """
        # Set up return values
        mock_issue_from_github.return_value = "Successful Call!"
        mock_github.return_value = self.mock_github_client
        self.mock_github_message['msg']['issue']['comments'] = 0

        # Call function
        response = u.handle_github_message(
            msg=self.mock_github_message,
            config=self.mock_config
        )
        # Assert that calls were made correctly
        mock_issue_from_github.assert_called_with('org/repo',
                                                  {'labels': ['custom_tag'], 'number': 'mock_number',
                                                   'comments': [], 'assignees': [{'fullname': 'mock_name'}],
                                                   'filter1': 'filter1',
                                                   'user': {'login': 'mock_login', 'fullname': 'mock_name'},
                                                   'milestone': 'mock_milestone'},
                                                  self.mock_config)
        mock_github.assert_called_with('mock_token')
        self.assertEqual('Successful Call!', response)
        self.mock_github_client.get_repo.assert_not_called()
        self.mock_github_repo.get_issue.assert_not_called()
        self.mock_github_issue.get_comments.assert_not_called()
        self.mock_github_client.get_user.assert_called_with('mock_login')

    @mock.patch(PATH + 'Github')
    @mock.patch('sync2jira.intermediary.Issue.from_github')
    def test_handle_github_message_successful(self,
                                              mock_issue_from_github,
                                              mock_github):
        """
        This function tests 'handle_github_message' where everything goes smoothly!
        """
        # Set up return values
        mock_issue_from_github.return_value = "Successful Call!"
        mock_github.return_value = self.mock_github_client

        # Call function
        response = u.handle_github_message(
            msg=self.mock_github_message,
            config=self.mock_config
        )

        # Assert that calls were made correctly
        mock_issue_from_github.assert_called_with('org/repo',
                                                  {'labels': ['custom_tag'], 'number': 'mock_number',
                                                   'comments': [{'body': 'mock_body', 'name': 'mock_user_login',
                                                                 'author': 'mock_username', 'changed': None,
                                                                 'date_created': 'mock_created_at', 'id': 'mock_id'}],
                                                   'assignees': [{'fullname': 'mock_name'}],
                                                   'filter1': 'filter1', 'user':
                                                       {'login': 'mock_login', 'fullname': 'mock_name'},
                                                   'milestone': 'mock_milestone'}, self.mock_config)
        mock_github.assert_called_with('mock_token')
        self.assertEqual('Successful Call!', response)
        self.mock_github_client.get_repo.assert_called_with('org/repo')
        self.mock_github_repo.get_issue.assert_called_with(number='mock_number')
        self.mock_github_issue.get_comments.assert_any_call()
        self.mock_github_client.get_user.assert_called_with('mock_login')

    @mock.patch(PATH + '_fetch_github_data')
    @mock.patch(PATH + '_github_link_field_to_dict')
    def test_get_all_github_issues(self,
                                   mock_github_link_field_to_dict,
                                   mock_fetch_github_data):
        """
        This tests the '_get_all_github_issues' function
        """
        # Set up return values
        get_return = MagicMock()
        get_return.json.return_value = [{'comments_url': 'mock_comments_url'}]
        get_return.headers = {'link': 'mock_link'}
        mock_fetch_github_data.return_value = get_return

        # Call the function
        response = list(u._get_all_github_issues(
            url='mock_url',
            headers='mock_headers'
        ))

        # Assert everything was called correctly
        mock_fetch_github_data.assert_any_call('mock_url', 'mock_headers')
        mock_fetch_github_data.assert_any_call('mock_comments_url', 'mock_headers')
        mock_github_link_field_to_dict.assert_called_with('mock_link')
        self.assertEqual('mock_comments_url', response[0]['comments_url'])

    @mock.patch(PATH + 'requests')
    def test_fetch_github_data_error(self,
                                     mock_requests):
        """
        Tests the '_fetch_github_data' function where we raise an IOError
        """
        # Set up return values
        get_return = MagicMock()
        get_return.__bool__ = mock.Mock(return_value=False)
        get_return.__nonzero__ = get_return.__bool__
        get_return.json.side_effect = Exception()
        get_return.text.return_value = {
            'issues': [
                {'assignee': 'mock_assignee'}
            ]

        }
        mock_requests.get.return_value = get_return

        # Call the function
        with self.assertRaises(IOError):
            u._fetch_github_data(
                url='mock_url',
                headers='mock_headers'
            )

        # Assert everything was called correctly
        mock_requests.get.assert_called_with('mock_url', headers='mock_headers')

    @mock.patch(PATH + 'requests')
    def test_fetch_github_data(self,
                                     mock_requests):
        """
        Tests the '_fetch_github_data' function where everything goes smoothly!
        """
        # Set up return values
        get_return = MagicMock()
        get_return.__bool__ = mock.Mock(return_value=True)
        get_return.__nonzero__ = get_return.__bool__
        mock_requests.get.return_value = get_return

        # Call the function

        response = u._fetch_github_data(
            url='mock_url',
            headers='mock_headers'
        )

        # Assert everything was called correctly
        mock_requests.get.assert_called_with('mock_url', headers='mock_headers')
        self.assertEqual(response, get_return)
