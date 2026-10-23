"""Offline signed distances for this project's flat static SDF scene."""
import math
import xml.etree.ElementTree as ET
import numpy as np


def transform(text):
    values = [float(v) for v in (text or '0 0 0 0 0 0').split()]
    if len(values) != 6 or not np.isfinite(values).all():
        raise ValueError('Finite xyz/rpy SDF pose required')
    x,y,z,r,p,a=values;c,s=math.cos,math.sin
    rz=np.array([[c(a),-s(a),0],[s(a),c(a),0],[0,0,1]])
    ry=np.array([[c(p),0,s(p)],[0,1,0],[-s(p),0,c(p)]])
    rx=np.array([[1,0,0],[0,c(r),-s(r)],[0,s(r),c(r)]])
    t=np.eye(4);t[:3,:3]=rz@ry@rx;t[:3,3]=[x,y,z]
    return t


def signed_box(points, half):
    q=np.abs(points)-half
    return np.linalg.norm(np.maximum(q,0),axis=1)+np.minimum(np.max(q,axis=1),0)


def signed_cylinder(points, radius, half_height):
    q=np.column_stack((np.linalg.norm(points[:,:2],axis=1)-radius,np.abs(points[:,2])-half_height))
    return np.linalg.norm(np.maximum(q,0),axis=1)+np.minimum(np.max(q,axis=1),0)


def load_obstacles(path):
    worlds=ET.parse(path).getroot().findall('world')
    world=worlds[0] if len(worlds)==1 else None
    if world is None or world.findall('.//include') or world.findall('.//frame'):
        raise ValueError('Only explicit flat SDF worlds are supported')
    if any(p.get('relative_to') or p.get('degrees') or p.get('rotation_format') for p in world.findall('.//pose')):
        raise ValueError('Only parent-relative xyz/rpy radians are supported')
    result=[]
    for model in world.findall('model'):
        if model.find('model') is not None or model.findtext('static') not in ('1','true'):
            raise ValueError('Only flat static models are supported')
        for link in model.findall('link'):
            for collision in link.findall('collision'):
                t=transform(model.findtext('pose'))@transform(link.findtext('pose'))@transform(collision.findtext('pose'))
                g=collision.find('geometry');name='/'.join([model.get('name'),link.get('name'),collision.get('name')])
                if g is None:raise ValueError('Collision has no geometry')
                if g.find('plane') is not None:
                    normal=np.array([float(v) for v in g.findtext('plane/normal','0 0 1').split()])
                    if (model.get('name')!='ground_plane' or not np.allclose(t[:3,3],0,atol=1e-6)
                            or not np.allclose(t[:3,:3]@normal,[0,0,1],atol=1e-6)):
                        raise ValueError('Only the explicit horizontal origin ground plane may be omitted')
                    continue
                if g.find('box') is not None:
                    shape=np.array([float(v) for v in g.findtext('box/size').split()])/2;kind='box'
                    if shape.shape!=(3,):raise ValueError('Box needs three dimensions')
                elif g.find('cylinder') is not None:
                    shape=np.array([float(g.findtext('cylinder/radius')),float(g.findtext('cylinder/length'))/2]);kind='cylinder'
                else:raise ValueError('Unsupported collision geometry: '+name)
                if not np.isfinite(shape).all() or np.any(shape<=0):raise ValueError('Invalid collision dimensions')
                result.append({'name':name,'kind':kind,'transform':t,'shape':shape})
    if not result:raise ValueError('No non-ground collision geometry')
    return result


def distances(points, obstacles):
    if not obstacles:raise ValueError('No obstacle geometry supplied')
    points=np.asarray(points,dtype=float)
    if points.ndim!=2 or points.shape[1]!=3 or not len(points) or not np.isfinite(points).all():
        raise ValueError('Finite nonempty Nx3 points required')
    closest=np.full(len(points),np.inf);names=np.full(len(points),'',dtype=object)
    for obstacle in obstacles:
        t=obstacle['transform'];local=(points-t[:3,3])@t[:3,:3];shape=obstacle['shape']
        d=signed_box(local,shape) if obstacle['kind']=='box' else signed_cylinder(local,*shape)
        better=d<closest;closest[better]=d[better];names[better]=obstacle['name']
    return closest,names


def segment_bound(start, end, obstacles, radius, max_step=.02):
    if not math.isfinite(radius) or radius<0 or not math.isfinite(max_step) or max_step<=0:
        raise ValueError('Valid radius and sampling step required')
    start=np.asarray(start,dtype=float);end=np.asarray(end,dtype=float)
    if start.shape!=(3,) or end.shape!=(3,) or not np.isfinite([start,end]).all():
        raise ValueError('Finite segment endpoints required')
    length=float(np.linalg.norm(end-start));segments=max(1,math.ceil(length/max_step))
    if segments>1_000_000:raise ValueError('Segment audit exceeds bounded sample count')
    points=np.linspace(start,end,segments+1);d,names=distances(points,obstacles);i=int(np.argmin(d))
    sampled=float(d[i]-radius);cover=length/segments/2
    # Signed distances are 1-Lipschitz; every segment point is within half a sampling gap.
    lower=sampled-cover
    return {'length_m':length,'samples':len(points),'sample_cover_radius_m':cover,
            'sampled_nominal_margin_m':sampled,'continuous_nominal_margin_lower_bound_m':lower,
            'nearest_sample_xyz':points[i].tolist(),'nearest_obstacle':str(names[i]),
            'static_non_ground_sphere_corridor_clear':lower>0}
