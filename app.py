import datetime

import django
import django.conf
import django.db
import django_micro


django_micro.configure({
    'DEBUG': True,
    'INSTALLED_APPS': [
        'django.contrib.auth',
        'django.contrib.contenttypes',
    ],
    'DATABASES': {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'db.sqlite3',
        },
    }
})


class Hotel(django.db.models.Model):

    title = django.db.models.CharField(max_length=128)
    likes = django.db.models.PositiveIntegerField()
    dislikes = django.db.models.PositiveIntegerField()

    class Meta:
        app_label = django_micro.get_app_label()


class Room(django.db.models.Model):

    title = django.db.models.CharField(max_length=128)
    hotel = django.db.models.ForeignKey(
        Hotel, on_delete=django.db.models.CASCADE, related_name='rooms')

    class Meta:
        app_label = django_micro.get_app_label()


class Reservation(django.db.models.Model):

    start = django.db.models.DateField()
    end = django.db.models.DateField()
    room = django.db.models.ForeignKey(
        Room, on_delete=django.db.models.CASCADE, related_name='reservations')
    user = django.db.models.ForeignKey(
        'auth.User', on_delete=django.db.models.CASCADE,
        related_name='reservations')

    class Meta:
        app_label = django_micro.get_app_label()


def dislike(hotel_id: int):
    hotel = Hotel.objects.get(pk=hotel_id)
    hotel.dislikes = django.db.models.F('dislikes') + 1
    hotel.save(update_fields=('dislikes',))


def get_rooms(move_in: datetime.date, move_out: datetime.date):
    return Room.objects.annotate(
        num_of_reservations=django.db.models.Sum(
            django.db.models.Case(
                django.db.models.When(
                    django.db.models.Q(
                        reservations__end__lte=move_in,
                    ) | django.db.models.Q(
                        reservations__start__gt=move_out,
                    ),
                    then=django.db.models.Value(0)
                ),
                default=django.db.models.Value(1)
            ),
        )
    ).annotate(
        sold_out=django.db.models.Case(
            django.db.models.When(
                num_of_reservations__gte=1,
                then=django.db.models.Value(True)
            ),
            default=django.db.models.Value(False)
        )
    )


def get_hotels_with_one_free_room(date: datetime.date):
    return Hotel.objects.annotate().annotate(
        num_of_reserved_rooms=django.db.models.Count(
            'rooms', filter=django.db.models.Q(
                django.db.models.Q(
                    rooms__reservations__end__lte=date,
                ) | django.db.models.Q(
                    rooms__reservations__start__gt=date,
                )
            )
        ),
        num_of_rooms=django.db.models.Count('rooms', distinct=True)
    ).annotate(
        free_rooms=django.db.models.F('num_of_rooms') - django.db.models.F('num_of_reserved_rooms')
    ).filter(
        free_rooms=1,
    )


application = django_micro.run()
