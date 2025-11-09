from examples.models import (
    Album,
    Artist,
    Track,
)
from iommi import Form
from iommi.admin import Admin
from iommi.main_menu import (
    EXTERNAL,
    M,
    MainMenu,
)

from examples import (
    form_examples,
    menu_examples,
    page_examples,
    supernaut,
    table_examples,
)

main_menu = MainMenu(
    items=dict(
        page=M(
            view=page_examples.IndexPage,
            items=dict(
                example_1=M(view=page_examples.HelloWorldPage),
                example_2=M(view=page_examples.page_view_example_2),
                example_3=M(view=page_examples.page_view_example_3),
                example_4=M(view=page_examples.page_view_example_4),
                live=M(view=page_examples.page_live),
            )
        ),
        form=M(
            view=form_examples.IndexPage,
            items=dict(
                example_1=M(view=form_examples.form_example_1),
                example_2=M(view=form_examples.form_example_2),
                example_3=M(view=form_examples.form_example_3),
                example_4=M(view=form_examples.form_example_4),
                example_5=M(view=form_examples.form_example_5),
                example_6=M(view=form_examples.form_example_6),
                example_7=M(view=form_examples.form_example_7),
                example_8=M(view=form_examples.form_example_8),
                example_9=M(view=form_examples.form_example_error_messages),
                example_10=M(view=form_examples.form_example_children_that_are_not_fields),
                example_11=M(view=form_examples.form_example_children_that_are_not_fields_declarative),
                example_12=M(view=form_examples.form_example_nested_forms),
                example_13=M(view=form_examples.form_example_file_upload),
                example_14=M(view=form_examples.form_example_field_groups),
                example_15=M(view=form_examples.form_example_dependent_fields),
                all_fields=M(view=form_examples.all_field_sorts),
            ),
        ),
        table=M(
            view=table_examples.IndexPage,
            items=dict(
                all_columns=M(view=table_examples.all_column_sorts),
                example_1=M(view=table_examples.table_readme_example_1),
                example_2=M(view=table_examples.table_readme_example_2),
                example_3=M(view=table_examples.table_auto_example_1),
                example_4=M(view=table_examples.table_auto_example_2),
                example_5=M(view=table_examples.table_kitchen_sink),
                example_6=M(view=table_examples.example_6_view),
                example_7=M(view=table_examples.table_two),
                example_8=M(view=table_examples.table_post_handler_on_lists),
                example_9=M(view=table_examples.extra_fields),
                example_10=M(view=table_examples.csv),
                example_11=M(view=table_examples.edit_table),
            )
        ),
        menu=M(
            view=menu_examples.menu_test,
        ),
        supernaut=M(
            view=supernaut.IndexPage,
            items=dict(
                albums=M(
                    view=supernaut.AlbumTable(auto__model=Album, columns__year__bulk__include=True),
                    items=dict(
                        create=M(view=Form.create(auto__model=Album)),
                        album=M(
                            path='<album_pk>/',
                            params={'album'},
                            view=supernaut.AlbumPage,
                            display_name=lambda album, **_: album.name,
                            url=lambda album, **_: album.get_absolute_url(),
                        ),
                    ),
                ),
                artists=M(
                    view=supernaut.ArtistTable(auto__model=Artist),
                    items=dict(
                        artist=M(
                            path='<artist_pk>/',
                            params={'artist'},
                            view=supernaut.ArtistPage,
                            display_name=lambda artist, **_: artist.name,
                            url=lambda artist, **_: artist.get_absolute_url(),
                        ),
                    ),
                ),
                tracks=M(view=supernaut.TrackTable(auto__model=Track)),
            ),
        ),
        iommi_admin=Admin.m(),
        login=M(
            view=EXTERNAL,
            display_name='Log in',
            url='/iommi-admin/login/?next=/',
            include=lambda request, **_: not request.user.is_authenticated,
        ),
        log_out=M(
            view=EXTERNAL,
            display_name='Log out',
            url='/iommi-admin/logout/',
            include=lambda request, **_: request.user.is_authenticated,
        ),
    ),
)


# sitemap = []
#
# def generate_sitemap(urlpatterns, indent=0):
#     for p in urlpatterns:
#         sitemap.append('     ' * indent + (str(p.pattern) or "''") + ' - > ' + str(p.callback.__name__ if p.callback else None))
#         if hasattr(p, 'url_patterns'):
#             generate_sitemap(p.url_patterns, indent + 1)
#
# generate_sitemap(main_menu.urlpatterns())
# print('!!!!')
# print('\n'.join(sitemap))
