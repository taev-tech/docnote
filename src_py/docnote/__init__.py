from __future__ import annotations

from collections.abc import Callable
from collections.abc import Sequence
from dataclasses import KW_ONLY
from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields as dc_fields
from enum import Enum
from functools import partial
from typing import Annotated
from typing import Any
from typing import Final
from typing import LiteralString
from typing import TypedDict

__all__ = [
    'DocnoteConfig',
    'DocnoteGroup',
    'Note',
    'docnote',
]


class MarkupLang(Enum):
    CLEANCOPY = ('cleancopy', 'clc')
    MARKDOWN = ('markdown', 'md')
    RST = ('rst',)


class ReftypeMarker(Enum):
    METACLASS = 'metaclass'
    DECORATOR = 'decorator'
    DECORATOR_SECOND_ORDER = 'decorator_2o'


@dataclass(frozen=True, slots=True)
class Note:
    """``Note``s are how you add actual notes for your documentation.
    They can be given their own config, or implicitly (and lazily)
    inherit the config from their parents. Use them within ``Annotated``
    names:

    > Example note usage
    __embed__: 'code/python'
        from typing import Annotated

        from docnote import Note

        MY_VAR: Annotated[int, Note('My special int')] = 7
    """
    value: str
    _: KW_ONLY
    config: DocnoteConfig | None = field(kw_only=True, default=None)


class DocnoteConfigParams(TypedDict, total=False):
    canonical_module: str
    canonical_name: str
    enforce_known_lang: bool
    markup_lang: str | MarkupLang
    include_in_docs: bool
    parent_group_name: str
    child_groups: Sequence[DocnoteGroup]
    ordering_index: int
    mark_special_reftype: ReftypeMarker
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True, kw_only=True)
class DocnoteConfig:
    """``DocnoteConfig``s can be used for a variety of reasons:
    ++  to control inference of the markup language when not explicitly
        passed, and whether or not to enforce rules around markup langs
    ++  to control whether an object should be included in the generated
        documentation or not, overriding inference rules
    ++  to define documentation sections (groups) that children can
        assign themselves to
    ++  to include themselves in a parent group

    Note that most config parameters are stack-bound: children will
    assume the values of their parents (unless the child defines its
    own overriding config). Some, however -- like the ``child_groups``
    setting -- are bound to only the exact object the config has been
    "attached" to.

    Configs can be attached:
    ++  to a module, by assigning it to the ``DOCNOTE_CONFIG`` name
    ++  to arbitrary names via ``Annotated``
    ++  to classes and functions via the ``docnote`` decorator

    **Note that module configs are inherited by submodules.** You can
    use this, for example, to define a default markup language in your
    entire project, by attaching a config to the toplevel
    ``__init__.py``.
    """
    canonical_module: Annotated[
            str | None,
            Note('''Set this to the fullname of a module (for example,
                ``foo.bar``) to override the automatically-detected canonical
                module for the attached object **and its children**.

                This is primarily useful for module-level constants that
                cannot otherwise be attributed to their parent module and
                objects defined within nostub modules, though it may also be
                helpful with re-exported objects, or when dealing with
                instances of imported classes.

                Typical usage is to set ``canonical_module=__name__``,
                pinning the object to the class in which it was defined.
                ''')
        ] = field(default=None, metadata={'docnote.stacked': True})

    canonical_name: Annotated[
            str | None,
            Note('''Set this to an explicit canonical name to override the
                default implicit normalization done by docs generation
                libraries.

                This is primarily useful for module-level constants
                defined within nostub modules and imported elsewhere,
                especially when imported under a different name (for example,
                if another module ran ``import my_constant as nostub_constant``
                on the example below).

                > Example typical usage: ``nostub_module.py``
                __embed__: 'code/python'
                    from typing import Annotated

                    from docnote import DocnoteConfig

                    my_constant: Annotated[
                        int,
                        DocnoteConfig(
                            # Not required to define ``canonical_name``, but
                            # usually paired together
                            canonical_module=__name__,
                            # Note that this name is typically redundant with
                            # the name within the module.
                            canonical_name='my_constant'
                        )] = 42
                ''')
        ] = field(default=None, metadata={'docnote.stacked': False})

    enforce_known_lang: Annotated[
            bool | None,
            Note('''When ``True``, this will ensure that the current config
                (and configs attached to its children) will enforce that the
                ``markup_lang`` is included in your specified allowlist of
                markup languages, **as determined by your docs generation
                library.**

                Note that the actual check **is not performed by docnote, and
                must be performed by your docs generation library.**
                ''')
        ] = field(default=None, metadata={'docnote.stacked': True})

    markup_lang: Annotated[
            str | MarkupLang | None,
            Note('''When specified, this sets the markup language to use
                for any ``Note`` instances on the attached object (and its
                children) that don't explicitly declare a ``lang`` value.
                ''')
        ] = field(default=None, metadata={'docnote.stacked': True})

    include_in_docs: Annotated[
            bool | None,
            Note('''Whether or not to include the attached object (and its
                children) in the generated documentation. By default
                (``None``), this will be inferred based on python conventions:
                names with a single underscore (or ``__mangled`` names) will
                be excluded, and others included.

                An explicit boolean value can be used to override this
                behavior, forcing exclusion of otherwise-conventionally-public
                objects, or inclusion of conventionally private ones.

                Note that under the following situation:
                ++  parent sets ``include_in_docs=False``
                ++  child sets ``include_in_docs=True``
                the end behavior is determined by the docs extraction library.
                ''')
        ] = field(default=None, metadata={'docnote.stacked': False})

    parent_group_name: Annotated[
            str | None,
            Note('''This assigns the attached object to a group within its
                parent by its name.

                Note that docnote itself **does not validate the name** at
                definition time; this is a deliberate choice to avoid library
                consumers from paying an import-time penalty for projects
                using docnotes.

                You should instead rely upon your docs generation library for
                validating these values, ideally as part of your CI/CD suite,
                git hooks, etc.
                ''')
        ] = field(default=None, metadata={'docnote.stacked': False})

    child_groups: Annotated[
            Sequence[DocnoteGroup] | None,
            Note('''This defines both the groups that should be available
                for immediate children to assign themselves to, as well as
                their desired ordering in the final documentation.

                **Note that this applies only to the immediate children of
                the scope the config was assigned to.** For example, if the
                config is assigned to a module, it will apply only to toplevel
                members of the module (classes, functions, etc defined directly
                as part of the module).
                ''')
        ] = field(default=None, metadata={'docnote.stacked': False})

    ordering_index: Annotated[
            int | None,
            Note('''Although implementations should ensure that the ordering
                of child items within a parent (or within its designated
                ``parent_group_name``) is ^^deterministic^^, it is by default
                nonetheless ^^unspecified and arbitrary.^^ In other words,
                though multiple identical docs builds should always produce
                the same result, the ordering of child members is, by default,
                completely up to the documentation generator's implementation.

                The ordering index can be used to override the default behavior
                and explicitly specify its position within the parent. Values
                function like indices in python: positive values are indexed
                from the start of the siblings list, negative values from the
                end, with the default, unordered siblings in-between.

                Ordering indices need not be sequential. All of the following
                would be valid, and must be sorted as shown:

                > Non-sequential indices
                __embed__: 'code/python'
                    [1, 3, 5, 7, None, -7, -6]
                    [None, -2, -1]
                    [0, 1, None, -9]
                    [0, 10, 20, None, -20, -10, -1]

                If two siblings have the same index, the ordering should be
                stable with respect to the default ordering. In other words,
                they should first be ordered by their indices, and then
                siblings with matching ``ordering_index`` values should be
                ordered by the documentation generator's default ordering
                strategy.
                ''')
        ] = field(default=None, metadata={'docnote.stacked': False})

    mark_special_reftype: Annotated[
            ReftypeMarker | None,
            Note('''Special reftypes (currently decorators and metaclasses)
                defined at the top level of a module **must** attach this to
                the object for stubbed imports to work correctly during
                extraction. For non-toplevel objects, the marker will
                nonetheless be included in the final object summary.

                > Example usage
                __embed__: 'code/python'
                    # When imported and used by other modules, this will
                    # now correctly be treated as a decorator during docnote
                    # extraction.
                    @docnote(DocnoteConfig(
                        mark_special_reftype=ReftypeMarker.DECORATOR))
                    def my_decorator[T: type | Callable](func: T) -> T:
                        ...

                    # (in some other module)
                    @my_decorator
                    def foo():
                        ...
                ''')
        ] = field(default=None, metadata={'docnote.stacked': False})

    metadata: Annotated[
            dict[str, Any] | None,
            Note('''Arbitrary metadata may be included in the config as
                an extension mechanism for docs generation libraries.

                Whether or not a particular key is inherited by children of
                the attached objects is up to the implementation of the
                docs generation library defining the metadata key.
                ''')
        ] = field(default=None, metadata={'docnote.stacked': None})

    def get_stackables(self) -> DocnoteConfigParams:
        """Gets all of the **non-None** params that are also marked as
        being stackable. Note that unlike dataclasses.asdict, this does
        not create any copies of the underlying objects.
        """
        retval: DocnoteConfigParams = {}
        for dc_field in dc_fields(self):
            if dc_field.metadata.get('docnote.stacked'):
                value = getattr(self, dc_field.name)
                if value is not None:
                    retval[dc_field.name] = value

        return retval

    def as_nontotal_dict(self) -> DocnoteConfigParams:
        """Gets all of the **non-None** params, regardless of whether
        they are stacked or not. Note that unlike dataclasses.asdict,
        this does not create any copies of the underlying objects.
        """
        retval: DocnoteConfigParams = {}
        for dc_field in dc_fields(self):
            value = getattr(self, dc_field.name)
            if value is not None:
                retval[dc_field.name] = value

        return retval

    def __post_init__(self):
        """The vast majority of checks are done by the docs generation
        library in order to avoid runtime consequences for libraries
        that use docnote. However, the one thing we ^^do^^ actually
        verify is that the group names are unique.
        """
        if self.child_groups is not None:
            group_names = {
                group.name for group in self.child_groups}
            if len(group_names) != len(self.child_groups):
                raise ValueError(
                    'Cannot have duplicate docnote group names for a single '
                    + 'attached object!')


# We have this purely for backwards compatibility. We set our own config for
# using cleancopy at the end of the module.
ClcNote: Annotated[
        Callable[[str], Note],
        DocnoteConfig(include_in_docs=False)
    ] = partial(Note, config=DocnoteConfig(markup_lang=MarkupLang.CLEANCOPY))
DOCNOTE_CONFIG_ATTR: Annotated[
        Final[LiteralString],
        Note('''Docs generation libraries should use this value to
            get access to any configs attached to objects via the
            ``docnote`` decorator.
            ''')
    ] = '_docnote_config'
DOCNOTE_CONFIG_ATTR_FOR_MODULES: Annotated[
        Final[LiteralString],
        Note('''Modules documented via docnote can defined a module-level
            ``DocnoteConfig`` at this attribute to customize the behavior
            of the module itself.
            ''')
    ] = 'DOCNOTE_CONFIG'


@dataclass(frozen=True, slots=True)
class DocnoteGroup:
    """``DocnoteGroup`` instances can be used to separate children of
    a particular object into groups for the purpose of documentation.
    For example, if you were defining an ``int`` subclass, you might
    take advantage of this to move all of the math-related methods into
    a separate section from additional application-specific methods
    added in the subclass.
    """
    name: Annotated[
        str,
        Note('''The name of the ``DocnoteGroup`` is used by children to
            assign themselves to the group.

            It might also be used by an automatic docs generation library in
            its description of the group.
            ''')]
    _: KW_ONLY
    description: Annotated[
            str | None,
            Note('''Groups may optionally include a description, which
                may be used by your docs generation library.
                ''')
        ] = None
    metadata: Annotated[
            dict[str, Any] | None,
            Note('''Groups may optionally include metadata, which
                may be used by your docs generation library.
                ''')
        ] = None


def docnote[T](
        config: DocnoteConfig
        ) -> Callable[[T], T]:
    """This decorator attaches a configuration to a decoratable object:

    > Example usage
    __embed__: 'code/python'
        from docnote import DocnoteConfig
        from docnote import docnote

        @docnote(DocnoteConfig(include_in_docs=False))
        def my_unconventional_private_function(): ...
    """
    return partial(_attach_config, config=config)


def _attach_config[T](to_decorate: T, *, config: DocnoteConfig) -> T:
    setattr(to_decorate, DOCNOTE_CONFIG_ATTR, config)
    return to_decorate


# This has to go after we define the DocnoteConfig class, so it might as well
# go at the very, very end
# Note that this is better than explicitly using ``ClcNote`` internally,
# because we can't use that before it's been defined. Bizzarely (I think
# because of the __future__ import) it will actually successfully exec the
# module if you do, but pyright freaks out.
DOCNOTE_CONFIG = DocnoteConfig(
    enforce_known_lang=True, markup_lang=MarkupLang.CLEANCOPY)
