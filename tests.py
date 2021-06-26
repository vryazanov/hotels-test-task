import datetime

import django.db.models
import factory.django
import pytest

import app

# need to import after `app` package in order to initialized
# django first
import django.contrib.auth.models  # noqa


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = django.contrib.auth.models.User


class HotelFactory(factory.django.DjangoModelFactory):

    likes = 0
    dislikes = 0

    class Meta:
        model = app.Hotel


class RoomFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = app.Room


class ReservationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = app.Reservation


@pytest.mark.django_db
def test_get_users_living_in_marylend():
    user_1 = UserFactory(username='User 1')
    user_2 = UserFactory(username='User 2')

    hotel = HotelFactory(title='Maryland')
    room_1 = RoomFactory(hotel=hotel)
    room_2 = RoomFactory(hotel=hotel)

    today = datetime.datetime.today().date()

    reservation_maryland_today = ReservationFactory(
        room=room_2,
        user=user_1,
        start=today - datetime.timedelta(days=1),
        end=today + datetime.timedelta(days=1),
    )
    reservation_maryland_old = ReservationFactory(
        room=room_2,
        user=user_1,
        start=today - datetime.timedelta(days=5),
        end=today - datetime.timedelta(days=3),
    )

    assert app.get_users_living_in('Maryland').get() == user_1


@pytest.mark.django_db
def test_concurrent_like_dislike():
    hotel = HotelFactory(title='Maryland', likes=0, dislikes=0)

    # simulate updating from another thread. no way to run real
    # threads because of sqlite is used
    app.Hotel.objects.update(dislikes=1)

    app.dislike(hotel.pk)

    hotel.refresh_from_db()
    assert hotel.dislikes == 2


@pytest.mark.django_db
def test_sold_out_annotation():
    user = UserFactory(username='User')

    hotel = HotelFactory(title='Maryland')
    room_1 = RoomFactory(hotel=hotel)
    room_2 = RoomFactory(hotel=hotel)
    room_3 = RoomFactory(hotel=hotel)

    today = datetime.datetime.today().date()

    reservation_today = ReservationFactory(
        user=user,
        room=room_1,
        start=today - datetime.timedelta(days=1),
        end=today + datetime.timedelta(days=1),
    )
    reservation_past = ReservationFactory(
        user=user,
        room=room_2,
        start=today - datetime.timedelta(days=2),
        end=today - datetime.timedelta(days=1),
    )
    reservation_future = ReservationFactory(
        user=user,
        room=room_3,
        start=today + datetime.timedelta(days=1),
        end=today + datetime.timedelta(days=2),
    )

    move_in = today - datetime.timedelta(days=10)
    move_out = today - datetime.timedelta(days=1)

    queryset = app.get_rooms(move_in, move_out)

    assert {room.id: room.sold_out for room in queryset} == {
        room_1.id: True,
        room_2.id: True,
        room_3.id: False,
    }


@pytest.mark.django_db
def test_sold_out_duplcates():
    # test if results have no duplicates because of outer join
    user = UserFactory(username='User')

    hotel = HotelFactory(title='Maryland')
    room = RoomFactory(hotel=hotel)

    today = datetime.datetime.today().date()

    ReservationFactory(
        user=user,
        room=room,
        start=today - datetime.timedelta(days=2),
        end=today - datetime.timedelta(days=1),
    )
    ReservationFactory(
        user=user,
        room=room,
        start=today - datetime.timedelta(days=1),
        end=today + datetime.timedelta(days=1),
    )

    move_in = today - datetime.timedelta(days=10)
    move_out = today + datetime.timedelta(days=10)

    queryset = app.get_rooms(move_in, move_out)
    
    assert len(list(app.get_rooms(move_in, move_out))) == 1


@pytest.mark.django_db
def test_free_room():
    user = UserFactory(username='User')

    hotel_1 = HotelFactory(title='Maryland')
    hotel_2 = HotelFactory(title='Hampton')
    hotel_3 = HotelFactory(title='No rooms')

    room_1 = RoomFactory(hotel=hotel_1)
    room_2 = RoomFactory(hotel=hotel_1)
    room_3 = RoomFactory(hotel=hotel_2)

    ReservationFactory(
        user=user,
        room=room_1,
        start=datetime.date(2021, 6, 15),
        end=datetime.date(2021, 6, 16),
    )
    ReservationFactory(
        user=user,
        room=room_1,
        start=datetime.date(2021, 6, 17),
        end=datetime.date(2021, 6, 18),
    )

    def get_ids(queryset):
        return [hotel.pk for hotel in queryset.order_by('pk')]

    queryset = app.get_hotels_with_one_free_room(datetime.date(2021, 6, 15))
    assert get_ids(queryset) == [hotel_1.pk, hotel_2.pk]


    queryset = app.get_hotels_with_one_free_room(datetime.date(2021, 6, 16))
    assert get_ids(queryset) == [hotel_2.pk]
