# (C) Copyright 2005-2020 Enthought, Inc., Austin, TX
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD
# license included in LICENSE.txt and may be redistributed only under
# the conditions described in the aforementioned license. The license
# is also available online at http://www.enthought.com/licenses/BSD.txt
#
# Thanks for using Enthought open source!

""" Integration tests between HasTraits and observe.
See tests in ``traits.observations`` for more targeted tests.
"""

import unittest

from traits.api import (
    Any,
    Bool,
    DelegatesTo,
    Dict,
    Event,
    HasTraits,
    Instance,
    Int,
    List,
    observe,
    Set,
    Str,
)
from traits.observation.api import (
    pop_exception_handler,
    push_exception_handler,
    trait,
)


class Student(HasTraits):
    """ Model for testing list + post_init (enthought/traits#275) """

    graduate = Event()


class Teacher(HasTraits):
    """ Model for testing list + post_init (enthought/traits#275) """

    students = List(Instance(Student))

    student_graduate_events = List()

    @observe(
        trait("students", notify=True)
        .list_items(notify=False)
        .trait("graduate"),
        post_init=True)
    def _student_graduate(self, event):
        self.student_graduate_events.append(event)


class TestHasTraitsObservePostInit(unittest.TestCase):
    """ Test for enthought/traits#275 """

    def setUp(self):
        push_exception_handler(reraise_exceptions=True)
        self.addCleanup(pop_exception_handler)

    def test_observe_post_init_true(self):
        # Resolves enthought/traits#275
        students = [Student() for _ in range(3)]
        teacher = Teacher(students=students)

        # No events as handler is created post-init
        self.assertEqual(len(teacher.student_graduate_events), 0)

        # when
        students[0].graduate = True

        # then
        self.assertEqual(len(teacher.student_graduate_events), 1)


# Integration tests for default initializer -----------------------------------


class Record(HasTraits):
    number = Int(10)

    default_call_count = Int()

    number_change_events = List()

    clicked = Event()

    def _number_default(self):
        self.default_call_count += 1
        return 99

    @observe('number')
    def handle_number_change(self, event):
        self.number_change_events.append(event)


class Album(HasTraits):

    records = List(Instance(Record))

    records_default_call_count = Int()

    record_number_change_events = List()

    name_to_records = Dict(Str, Record)

    name_to_records_default_call_count = Int()

    name_to_records_clicked_events = List()

    def _records_default(self):
        self.records_default_call_count += 1
        return [Record()]

    @observe(trait("records").list_items().trait("number"))
    def handle_record_number_changed(self, event):
        self.record_number_change_events.append(event)

    def _name_to_records_default(self):
        self.name_to_records_default_call_count += 1
        return {"Record": Record()}

    @observe("name_to_records:items:clicked")
    def handle_event(self, event):
        self.name_to_records_clicked_events.append(event)


class TestHasTraitsObserverDefaultHandler(unittest.TestCase):
    """ Test the behaviour with dynamic default handler + container. """

    def setUp(self):
        push_exception_handler(reraise_exceptions=True)
        self.addCleanup(pop_exception_handler)

    def test_default_not_called_if_init_contains_value(self):
        record = Record(number=123)
        # enthought/traits#94
        self.assertEqual(record.default_call_count, 1)
        self.assertEqual(len(record.number_change_events), 1)
        event, = record.number_change_events
        self.assertEqual(event.object, record)
        self.assertEqual(event.name, "number")
        self.assertEqual(event.old, 99)
        self.assertEqual(event.new, 123)

    def test_observe_extended_trait_in_list(self):
        album = Album()

        # default is not called.
        self.assertEqual(album.records_default_call_count, 0)
        self.assertEqual(len(album.record_number_change_events), 0)

        # But the observers are hooked up
        # when
        album.records[0].number += 1

        # then
        self.assertEqual(album.records_default_call_count, 1)
        self.assertEqual(len(album.record_number_change_events), 1)
        event, = album.record_number_change_events
        self.assertEqual(event.object, album.records[0])
        self.assertEqual(event.name, "number")
        self.assertEqual(event.old, 99)
        self.assertEqual(event.new, 100)

    def test_observe_extended_trait_in_default_dict(self):
        # Test for enthought/traits#279
        album = Album()

        self.assertEqual(album.name_to_records_default_call_count, 0)
        self.assertEqual(len(album.name_to_records_clicked_events), 0)

        # when
        album.name_to_records["Record"].clicked = True

        # then
        self.assertEqual(len(album.name_to_records_clicked_events), 1)


# Integration tests for nested List and extended traits -----------------------

class SingleValue(HasTraits):

    value = Int()


class ClassWithListOfInstance(HasTraits):

    list_of_instances = List(Instance(SingleValue))


class ClassWithListOfListOfInstance(HasTraits):

    list_of_list_of_instances = List(List(Instance(SingleValue)))


class TestHasTraitsObserveListOfInstance(unittest.TestCase):

    def setUp(self):
        push_exception_handler(reraise_exceptions=True)
        self.addCleanup(pop_exception_handler)

    def test_observe_instance_in_nested_list(self):

        container = ClassWithListOfListOfInstance()
        events = []
        handler = events.append
        container.observe(
            expression=(
                trait("list_of_list_of_instances", notify=False)
                .list_items(notify=False)
                .list_items(notify=False)
                .trait("value")
            ),
            handler=handler,
        )

        # sanity check
        single_value_instance = SingleValue()
        inner_list = [single_value_instance]
        container.list_of_list_of_instances.append(inner_list)
        self.assertEqual(len(events), 0)

        # when
        single_value_instance.value += 1

        # then
        event, = events
        self.assertEqual(event.object, single_value_instance)
        self.assertEqual(event.name, "value")
        self.assertEqual(event.old, 0)
        self.assertEqual(event.new, 1)

    def test_nested_list_reassigned_value_compared_equally(self):
        container = ClassWithListOfListOfInstance()
        events = []
        handler = events.append
        container.observe(
            expression=(
                trait("list_of_list_of_instances", notify=False)
                .list_items(notify=False)
                .list_items(notify=False)
                .trait("value")
            ),
            handler=handler,
        )

        inner_list = [SingleValue()]
        container.list_of_list_of_instances = [inner_list]
        # sanity check
        self.assertEqual(len(events), 0)

        # assignment of a list that compares equally should be handled
        # correctly.
        # This relies on TraitList not trying to suppress notifications
        # when new values compared equally to old values.
        container.list_of_list_of_instances[0] = inner_list
        second_instance = SingleValue()
        container.list_of_list_of_instances[0].append(second_instance)
        self.assertEqual(len(events), 0)

        # when
        second_instance.value += 1

        # then
        event, = events
        self.assertEqual(event.object, second_instance)
        self.assertEqual(event.name, "value")
        self.assertEqual(event.old, 0)
        self.assertEqual(event.new, 1)

    def test_duplicated_items_tracked(self):
        # test for enthought/traits#237
        container = ClassWithListOfInstance()
        events = []
        handler = events.append
        container.observe(
            expression=(
                trait("list_of_instances", notify=False)
                .list_items(notify=False)
                .trait("value")
            ),
            handler=handler,
        )

        instance = SingleValue()
        # The item is repeated.
        container.list_of_instances.append(instance)
        container.list_of_instances.append(instance)
        self.assertEqual(len(events), 0)

        # when
        instance.value += 1

        # then
        self.assertEqual(len(events), 1)
        events.clear()

        # when
        container.list_of_instances.pop()
        instance.value += 1

        # then
        self.assertEqual(len(events), 1)
        events.clear()

        # when
        container.list_of_instances.pop()
        instance.value += 1

        # then
        self.assertEqual(len(events), 0)


# Integration tests for nested Dict and extended traits -----------------------


class ClassWithDictOfInstance(HasTraits):

    name_to_instance = Dict(Str, Instance(SingleValue))


class TestHasTraitsObserveDictOfInstance(unittest.TestCase):

    def setUp(self):
        push_exception_handler(reraise_exceptions=True)
        self.addCleanup(pop_exception_handler)

    def test_observe_instance_in_dict(self):
        container = ClassWithDictOfInstance()
        events = []
        handler = events.append
        container.observe(
            handler=handler,
            expression=(
                trait("name_to_instance", notify=False)
                .dict_items(notify=False)
                .trait("value")
            ),
        )

        single_value_instance = SingleValue()
        container.name_to_instance = {"name": single_value_instance}
        # sanity check
        self.assertEqual(len(events), 0)

        # when
        single_value_instance.value += 1

        # then
        event, = events
        self.assertEqual(event.object, single_value_instance)
        self.assertEqual(event.name, "value")
        self.assertEqual(event.old, 0)
        self.assertEqual(event.new, 1)


# Integration tests for Set and extended traits ------------------------------


class ClassWithSetOfInstance(HasTraits):

    instances = Set(Instance(SingleValue))

    instances_compat = Set(Instance(SingleValue))


class TestHasTraitsObserveSetOfInstance(unittest.TestCase):

    def setUp(self):
        push_exception_handler(reraise_exceptions=True)
        self.addCleanup(pop_exception_handler)

    def test_observe_instance_in_set(self):
        container = ClassWithSetOfInstance()
        events = []
        handler = events.append
        container.observe(
            handler=handler,
            expression=(
                trait("instances", notify=False)
                .set_items(notify=False)
                .trait("value")
            ),
        )

        single_value_instance = SingleValue()
        container.instances = set([single_value_instance])
        # sanity check
        self.assertEqual(len(events), 0)

        # when
        single_value_instance.value += 1

        # then
        event, = events
        self.assertEqual(event.object, single_value_instance)
        self.assertEqual(event.name, "value")
        self.assertEqual(event.old, 0)
        self.assertEqual(event.new, 1)


# Integration test for maintaining and differentiating observers --------------

class Potato(HasTraits):

    name = Str()


class PotatoBag(HasTraits):

    potatos = List(Instance(Potato))


class Crate(HasTraits):

    potato_bags = List(PotatoBag)


class TestHasTraitsObserverDifferentiateParent(unittest.TestCase):

    def test_shared_instance_but_different_target(self):
        # If the comparison of targets is removed from
        # TraitEventNotifier.equals, this test would fail.
        potato = Potato()
        potato_bag = PotatoBag(potatos=[potato])
        crate1 = Crate(potato_bags=[potato_bag])
        crate2 = Crate(potato_bags=[potato_bag])

        # when
        events = []
        handler = events.append
        crate1.observe(
            handler, "potato_bags:items:potatos:items:name",
        )
        crate2.observe(
            handler, "potato_bags:items:potatos:items:name",
        )
        potato.name = "King Edward"

        # then
        # there are two notifiers, because they are observed from different
        # objects.
        self.assertEqual(len(events), 2)

    def test_shared_instance_same_graph_different_target(self):

        crate1 = Crate()
        crate2 = Crate()

        # given
        events = []
        handler = events.append
        crate1.observe(handler, "potato_bags:items:potatos:items:name")
        crate2.observe(handler, "potato_bags:items:potatos:items:name")

        new_potato = Potato()
        new_potato_bag = PotatoBag(potatos=[new_potato])
        crate1.potato_bags = [new_potato_bag]
        crate2.potato_bags = [new_potato_bag]
        new_potato.name = "King Edward I"
        self.assertEqual(len(events), 2)
        events.clear()

        # when
        # remove the second observer
        crate2.observe(
            handler, "potato_bags:items:potatos:items:name", remove=True)
        new_potato.name = "King Edward II"

        # then
        self.assertEqual(len(events), 1)
        events.clear()

        # then
        # This check the observer is maintained.
        maris_piper = Potato()
        crate2.potato_bags[0].potatos.append(maris_piper)
        crate1.potato_bags = []
        self.assertEqual(len(events), 0)  # sanity check

        # this fails if targets were not compared.
        maris_piper.name = "Maris Piper"
        self.assertEqual(len(events), 0)


# Integration test for the special event metadata ----------------------------

class FooWithEventMetadata(HasTraits):
    val = Str(event="the_trait")

    @observe("the_trait")
    def _handle_the_trait_changed(self, event):
        pass


class TestSpecialEvent(unittest.TestCase):
    """ Test the 'event' metadata... won't work with ``observe``!
    """

    def setUp(self):
        push_exception_handler(reraise_exceptions=True)
        self.addCleanup(pop_exception_handler)

    def test_events(self):

        with self.assertRaises(ValueError) as exception_cm:
            # Attempt to attach the observer will fail because
            # the "the_trait" is not actually a trait on the object.
            FooWithEventMetadata()

        self.assertIn(
            "Trait named 'the_trait' not found",
            str(exception_cm.exception),
        )


# Integration test for when the observer is not appropriate for the data ------

class Person(HasTraits):
    name = Str()


class Team(HasTraits):
    leader = Instance(Person)

    member_names = List(Str())

    any_value = Any()


class TestObserverError(unittest.TestCase):

    def setUp(self):
        push_exception_handler(reraise_exceptions=True)
        self.addCleanup(pop_exception_handler)

    def test_trait_is_not_list(self):

        team = Team()
        # The `list_items` should not be used here.
        # Error is not emitted now as leader is not defined so there is no
        # way to check.
        team.observe(lambda e: None, trait("leader").list_items())

        person = Person()
        with self.assertRaises(ValueError) as exception_cm:
            team.leader = person

        self.assertIn(
            "Expected a TraitList to be observed",
            str(exception_cm.exception),
        )

    def test_items_on_a_list_not_observable_by_named_trait(self):
        # The member_names is a list of str, attempt to observe extended
        # trait on them should fail.
        team = Team()

        team.observe(
            lambda e: None,
            trait("member_names").list_items().trait("does_not_exist")
        )

        with self.assertRaises(ValueError) as exception_cm:
            team.member_names = ["Paul"]

        self.assertEqual(
            str(exception_cm.exception),
            "Trait named 'does_not_exist' not found on 'Paul'."
        )

    def test_extended_trait_on_any_value(self):
        team = Team()
        team.any_value = 123

        with self.assertRaises(ValueError) as exception_cm:
            team.observe(
                lambda e: None, trait("any_value").trait("does_not_exist"))

        self.assertEqual(
            str(exception_cm.exception),
            "Trait named 'does_not_exist' not found on 123."
        )

    def test_no_new_trait_added(self):
        # Test enthought/traits#447 can be avoided with observe
        team = Team()
        team.observe(lambda e: None, trait("leader").trait("does_not_exist"))

        with self.assertRaises(ValueError):
            team.leader = Person()

        self.assertNotIn("does_not_exist", team.leader.trait_names())


# Integration test with DelegateTo --------------------------------------------

class Dummy(HasTraits):
    x = Int(10)


class Dummy2(HasTraits):
    y = Int(20)
    dummy = Instance(Dummy)


class DelegateMess(HasTraits):
    dummy1 = Instance(Dummy, args=())
    dummy2 = Instance(Dummy2)

    y = DelegatesTo("dummy2")

    handler_called = Bool(False)

    def _dummy2_default(self):
        # Create `self.dummy1`
        return Dummy2(dummy=self.dummy1)

    @observe("dummy1.x")
    def _on_dummy1_x(self, event):
        self.handler_called = True


class TestDelegateToInteraction(unittest.TestCase):

    def test_delegate_initializer(self):
        mess = DelegateMess()
        self.assertFalse(mess.handler_called)
        mess.dummy1.x = 20
        self.assertTrue(mess.handler_called)
