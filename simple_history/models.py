import copy
import datetime
from django.db import models
from fields import SimpleHistoryForeignKey,SimpleHistoryOneToOneField
from manager import HistoryDescriptor

class HistoricalRecords(object):
    def __init__(self,pk_field=None):
        if pk_field is None:
            self.pk_field = models.AutoField(primary_key=True)
        elif isinstance(pk_field, models.Field) \
        and pk_field.primary_key:
            self.pk_field = pk_field
        else:   
            raise ValueError("If supplied, 'pk_field' must subclass 'django.db.models.fields.Field' with a primary_key attribute of True.")
        super(HistoricalRecords,self).__init__()
    
    def contribute_to_class(self, cls, name):
        self.manager_name = name
        models.signals.class_prepared.connect(self.finalize, sender=cls)

    def finalize(self, sender, **kwargs):
        history_model = self.create_history_model(sender)

        # The HistoricalRecords object will be discarded,
        # so the signal handlers can't use weak references.
        models.signals.post_save.connect(self.post_save, sender=sender,
                                         weak=False)
        models.signals.post_delete.connect(self.post_delete, sender=sender,
                                           weak=False)

        descriptor = HistoryDescriptor(history_model)
        setattr(sender, self.manager_name, descriptor)

    def create_history_model(self, model):
        """
        Creates a historical model to associate with the model provided.
        """
        attrs = self.copy_fields(model)
        attrs.update(self.get_extra_fields(model))
        attrs.update(Meta=type('Meta', (), self.get_meta_options(model)))
        name = 'Historical%s' % model._meta.object_name
        return type(name, (models.Model,), attrs)

    def copy_fields(self, model):
        """
        Creates copies of the model's original fields, returning
        a dictionary mapping field name to copied field object.
        """
        # Though not strictly a field, this attribute
        # is required for a model to function properly.
        fields = {'__module__': model.__module__}

        for field in model._meta.fields:
            field = copy.copy(field)
            fk = None

            if isinstance(field, models.AutoField):
                # The historical model gets its own AutoField, so any
                # existing one must be replaced with an IntegerField.
                field.__class__ = models.IntegerField

            if isinstance(field, models.ForeignKey):
                # do not assume that the ForeignKey
                # points to an AutoField
                try:
                    to_field = field.rel.get_related_field()
                except AttributeError:
                    try:
                        to_field = field.sh_to_field
                    except AttributeError:
                        if isinstance(field.rel.to,basestring) \
                        and not isinstance(field,SimpleHistoryForeignKey) \
                        or not isinstance(field,SimpleHistoryOneToOneField):
                            raise TypeError("ForeignKey and OneToOne fields with a string 'to' must inherit from SimpleHistoryForeignKey or SimpleHistoryOneToOneField.")
                        else:
                            raise
                if isinstance(to_field, models.AutoField): 
                    field.__class__ = models.IntegerField
                else:
                    # If to_field is not an AutoField, assume that
                    # it is safe to use as-is on the history table.
                    # However, some attributes should be ignored.
                    field.__class__ = to_field.__class__
                    excluded_prefixes = ("_","__")
                    excluded_attributes = (
                        "rel",
                        "creation_counter",
                        "validators",
                        "error_messages",
                        "attname",
                        "column",
                        "help_text",
                        "name",
                        "model",
                        "unique_for_year",
                        "unique_for_date",
                        "unique_for_month",
                        "db_tablespace",
                        "db_index",
                        "db_column",
                        "default",
                        "auto_created",
                    )
                    for key, val in to_field.__dict__.iteritems():
                        if isinstance(key, basestring) \
                        and not key.startswith(excluded_prefixes) \
                        and not key in excluded_attributes:
                            setattr(field,key,val)
                    
                #ughhhh. open to suggestions here
                try:
                    field.rel = None
                except:
                    pass
                try:
                    field.related = None
                except:
                    pass
                try:
                    field.related_query_name = None
                except:
                    pass
                field.null = True
                field.blank = True
                fk = True
            else:
                fk = False

            if field.primary_key or field.unique:
                # Unique fields can no longer be guaranteed unique,
                # but they should still be indexed for faster lookups.
                field.primary_key = False
                field._unique = False
                field.db_index = True
            if fk:
                fields[field.name+"_id"] = field
            else:
                fields[field.name] = field

        return fields

    def get_extra_fields(self, model):
        """
        Returns a dictionary of fields that will be added to the historical
        record model, in addition to the ones returned by copy_fields below.
        """
        rel_nm = '_%s_history' % model._meta.object_name.lower()
        return {
            'history_id': self.pk_field,
            'history_date': models.DateTimeField(default=datetime.datetime.now),
            'history_type': models.CharField(max_length=1, choices=(
                ('+', 'Created'),
                ('~', 'Changed'),
                ('-', 'Deleted'),
            )),
            'history_object': HistoricalObjectDescriptor(model),
            '__unicode__': lambda self: u'%s as of %s' % (self.history_object,
                                                          self.history_date)
        }

    def get_meta_options(self, model):
        """
        Returns a dictionary of fields that will be added to
        the Meta inner class of the historical record model.
        """
        return {
            'ordering': ('-history_date',),
        }

    def post_save(self, instance, created, **kwargs):
        self.create_historical_record(instance, created and '+' or '~')

    def post_delete(self, instance, **kwargs):
        self.create_historical_record(instance, '-')

    def create_historical_record(self, instance, type):
        manager = getattr(instance, self.manager_name)
        attrs = {}
        for field in instance._meta.fields:
            attrs[field.attname] = getattr(instance, field.attname)
        manager.create(history_type=type, **attrs)

class HistoricalObjectDescriptor(object):
    def __init__(self, model):
        self.model = model

    def __get__(self, instance, owner):
        values = (getattr(instance, f.attname) for f in self.model._meta.fields)
        return self.model(*values)
