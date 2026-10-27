"""Private provisioning clients used by student experiment controls."""
import json,pathlib,logging,contextlib
from pygnmi.client import gNMIclient
from pygnmi.spec.v080 import gnmi_pb2,gnmi_pb2_grpc
from google.protobuf.json_format import ParseDict,MessageToDict
from ncclient import manager
import grpc
logging.disable(logging.CRITICAL)
STATE=pathlib.Path('/var/lib/seminar-lab')
LAB=STATE/'runtime/clab-seminar'
HOSTS={'r1':'10.79.0.12','r2':'10.79.0.13'}
def credentials():return json.loads((STATE/'device-credentials.json').read_text())
@contextlib.contextmanager
def gnmi(node,operator=True):
 c=credentials();user='operator' if operator else 'observer'
 with gNMIclient(target=(HOSTS[node],57400),username=user,password=c[user],path_root=str(LAB/'.tls/ca/ca.pem'),gnmi_timeout=15) as g:yield g

