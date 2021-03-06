from django import forms
from django.core.exceptions import ValidationError
from django.forms.utils import flatatt
from django.test import SimpleTestCase
from django.utils import six

from enumchoicefield.enum import PrettyEnum
from enumchoicefield.forms import EnumField, EnumSelect


class MyEnum(PrettyEnum):
    foo = "Foo"
    bar = "Bar"
    baz = "Baz Quux"


class SelectTestCase(SimpleTestCase):
    def assertSelectOptions(self, html, options, name='choice'):
        if six.PY3:
            # Python3 enums have the correct order of options
            attrs = {'id': 'id_' + name, 'name': name}
            select = '<select{attrs}>{options}</select>'.format(
                attrs=flatatt(attrs), options=''.join(options))
            self.assertHTMLEqual(select, html)
        else:
            # Python2 enums have an arbitary order
            for option in options:
                self.assertInHTML(option, html)


class TestEnumForms(SelectTestCase):

    class EnumForm(forms.Form):
        choice = EnumField(MyEnum)

    def test_enum_field(self):
        form = self.EnumForm()
        self.assertIsInstance(form.fields['choice'].widget, EnumSelect)

    def test_rendering(self):
        form = self.EnumForm()
        html = six.text_type(form['choice'])
        self.assertSelectOptions(html, [
            '<option value="foo">Foo</option>',
            '<option value="bar">Bar</option>',
            '<option value="baz">Baz Quux</option>',
        ])

    def test_initial(self):
        form = self.EnumForm(initial={'choice': MyEnum.bar})
        html = six.text_type(form['choice'])
        self.assertInHTML('<option value="bar" selected>Bar</option>', html)

    def test_submission(self):
        form = self.EnumForm(data={'choice': 'baz'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['choice'], MyEnum.baz)

    def test_empty_submission(self):
        form = self.EnumForm(data={'choice': ''})
        self.assertFalse(form.is_valid())

    def test_missing_submission(self):
        form = self.EnumForm(data={})
        self.assertFalse(form.is_valid())

    def test_invalid_submission(self):
        form = self.EnumForm(data={'choice': 'nope'})
        self.assertFalse(form.is_valid())


class TestOptionalEnumForms(SelectTestCase):

    class EnumForm(forms.Form):
        choice = EnumField(MyEnum, required=False)

    def test_enum_field(self):
        form = self.EnumForm()
        self.assertIsInstance(form.fields['choice'].widget, EnumSelect)

    def test_rendering(self):
        form = self.EnumForm()
        html = six.text_type(form['choice'])
        self.assertSelectOptions(html, [
            '<option value="">---------</option>',
            '<option value="foo">Foo</option>',
            '<option value="bar">Bar</option>',
            '<option value="baz">Baz Quux</option>',
        ])

    def test_initial(self):
        form = self.EnumForm(initial={'choice': MyEnum.bar})
        html = six.text_type(form['choice'])
        self.assertInHTML('<option value="bar" selected>Bar</option>', html)

    def test_submission(self):
        form = self.EnumForm(data={'choice': 'baz'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['choice'], MyEnum.baz)

    def test_empty_submission(self):
        form = self.EnumForm(data={'choice': ''})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['choice'], None)

    def test_missing_submission(self):
        form = self.EnumForm(data={})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['choice'], None)


class TestComplicatedForm(SelectTestCase):

    class EnumForm(forms.Form):
        choice = EnumField(MyEnum)
        number = forms.IntegerField()

    def test_valid_form(self):
        form = self.EnumForm(data={'choice': 'foo', 'number': '10'})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data, {
            'choice': MyEnum.foo, 'number': 10})

    def test_invalid_number(self):
        form = self.EnumForm(data={'choice': 'bar', 'number': 'abc'})
        self.assertFalse(form.is_valid())
        html = six.text_type(form['choice'])
        self.assertSelectOptions(html, [
            '<option value="foo">Foo</option>',
            '<option value="bar" selected>Bar</option>',
            '<option value="baz">Baz Quux</option>',
        ])

    def test_invalid_choice(self):
        form = self.EnumForm(data={'choice': 'nope', 'number': '10'})
        self.assertFalse(form.is_valid())
        html = six.text_type(form['choice'])
        self.assertSelectOptions(html, [
            '<option value="foo">Foo</option>',
            '<option value="bar">Bar</option>',
            '<option value="baz">Baz Quux</option>',
        ])


class TestLimitedMembers(SelectTestCase):
    members = [MyEnum.baz, MyEnum.foo]

    def setUp(self):

        class EnumForm(forms.Form):
            choice = EnumField(MyEnum, members=self.members)

        self.EnumForm = EnumForm

    def test_field(self):
        field = EnumField(MyEnum)
        self.assertEqual(field.members, list(MyEnum))

    def test_limited_members(self):
        form = self.EnumForm()
        self.assertEqual(form['choice'].field.members, self.members)
        html = six.text_type(form['choice'])
        self.assertSelectOptions(html, [
            '<option value="baz">Baz Quux</option>',
            '<option value="foo">Foo</option>',
        ])

    def test_invalid_choice(self):
        form = self.EnumForm({'choice': 'bar'})
        self.assertFalse(form.is_valid())

    def test_valid_choice(self):
        form = self.EnumForm({'choice': 'baz'})
        self.assertTrue(form.is_valid())
        html = six.text_type(form['choice'])
        self.assertSelectOptions(html, [
            '<option value="baz" selected>Baz Quux</option>',
            '<option value="foo">Foo</option>',
        ])


class TestEnumField(SelectTestCase):
    # The EnumField instance to test with. It is missing MyEnum.bar
    field = EnumField(MyEnum, members=[MyEnum.baz, MyEnum.foo])

    def test_prepare_value(self):
        self.assertEqual(self.field.prepare_value(None), None)
        self.assertEqual(self.field.prepare_value(''), None)
        self.assertEqual(self.field.prepare_value(MyEnum.baz), 'baz')

    def test_to_python(self):
        self.assertEqual(self.field.to_python(None), None)
        self.assertEqual(self.field.to_python(''), None)
        self.assertEqual(self.field.to_python('baz'), MyEnum.baz)

    def test_to_python_invalid(self):
        with self.assertRaises(ValidationError):
            self.field.to_python('nope')

    def test_to_python_non_member(self):
        with self.assertRaises(ValidationError):
            self.field.to_python('bar')
