"""
~~~~~~~~~~~~~~~~~~~~~~~
Test Models
~~~~~~~~~~~~~~~~~~~~~~~
"""
from django.db.models import Model, CharField, ForeignKey, OneToOneField
from django.db.models.base import ModelBase
from models import HistoricalRecords

class TestModelBase(ModelBase):
    def _prepare(cls):
        # replace the default AutoField with a CharField
        needs_primary_key = True
        for field in cls._meta.fields:
            if field.primary_key:
                needs_primary_key = False
                break
        if needs_primary_key:
            auto = CharField(primary_key=True,max_length=10)
            cls.add_to_class('id', auto)
        
        # create the history records
        history_field = HistoricalRecords()
        cls.add_to_class('history', history_field)
        
        # call the real _prepare() method
        super(TestModelBase,cls)._prepare()

class TestModel(Model):
    __metaclass__ = TestModelBase
    
    class Meta:
        abstract = True
    
    def __unicode__(self):
        return '%s object: %s' % (self.__class__.__name__, self.pk)
    
class A(TestModel):
    pass

class B(TestModel):
    a = ForeignKey(A)

class C(TestModel):
    a = OneToOneField(A)

"""
~~~~~~~~~~~~~~~~~~~~~~~
Test Case
~~~~~~~~~~~~~~~~~~~~~~~
"""
from django.test import TestCase

class Tests(TestCase):
    def test_alphanumeric_pk(self):
        a = A()
        a.pk = "abcdef1234"
        a.save()
    
    def test_alphanumeric_fk(self):
        a = A()
        a.pk = "abcdef1234"
        a.save()        
        
        b = B()
        b.pk = "hijklm5678"
        b.a = a
        b.save()
        
    def test_alphanumeric_o2o(self):
        a = A()
        a.pk = "abcdef1234"
        a.save()
        
        c = C()
        c.pk = "hijklm5678"
        c.a = a
        c.save()