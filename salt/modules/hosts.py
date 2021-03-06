'''
Manage the information in the hosts file
'''

# Import python libs
import os

# Import salt libs
import salt.utils
import salt.utils.odict as odict


# pylint: disable-msg=C0103
def __get_hosts_filename():
    '''
    Return the path to the appropriate hosts file
    '''
    # TODO: Investigate using  "%SystemRoot%\system32" for this
    if salt.utils.is_windows():
        return 'C:\Windows\System32\drivers\etc\hosts'

    return __salt__['config.option']('hosts.file')


def _list_hosts():
    '''
    Return the hosts found in the hosts file in as an OrderedDict
    '''
    hfn = __get_hosts_filename()
    ret = odict.OrderedDict()
    if not os.path.isfile(hfn):
        return ret
    with salt.utils.fopen(hfn) as ifile:
        for line in ifile:
            line = line.strip()
            if not line:
                continue
            if line.startswith('#'):
                continue
            comps = line.split()
            ip = comps.pop(0)
            ret.setdefault(ip, []).extend(comps)
    return ret


def list_hosts():
    '''
    Return the hosts found in the hosts file in this format::

        {'<ip addr>': ['alias1', 'alias2', ...]}

    CLI Example::

        salt '*' hosts.list_hosts
    '''
    # msgpack does not like OrderedDict's
    return dict(_list_hosts())


def get_ip(host):
    '''
    Return the ip associated with the named host

    CLI Example::

        salt '*' hosts.get_ip <hostname>
    '''
    hosts = _list_hosts()
    if not hosts:
        return ''
    # Look for the op
    for addr in hosts:
        if host in hosts[addr]:
            return addr
    # ip not found
    return ''


def get_alias(ip):
    '''
    Return the list of aliases associated with an ip

    CLI Example::

        salt '*' hosts.get_alias <ip addr>
    '''
    hosts = _list_hosts()
    if ip in hosts:
        return hosts[ip]
    return []


def has_pair(ip, alias):
    '''
    Return true if the alias is set

    CLI Example::

        salt '*' hosts.has_pair <ip> <alias>
    '''
    hosts = _list_hosts()
    return ip in hosts and alias in hosts[ip]


def set_host(ip, alias):
    '''
    Set the host entry in the hosts file for the given ip, this will overwrite
    any previous entry for the given ip

    CLI Example::

        salt '*' hosts.set_host <ip> <alias>
    '''
    hfn = __get_hosts_filename()
    ovr = False
    if not os.path.isfile(hfn):
        return False
    lines = salt.utils.fopen(hfn).readlines()
    for ind in range(len(lines)):
        tmpline = lines[ind].strip()
        if not tmpline:
            continue
        if tmpline.startswith('#'):
            continue
        comps = tmpline.split()
        if comps[0] == ip:
            if not ovr:
                lines[ind] = ip + '\t\t' + alias + '\n'
                ovr = True
            else:  # remove other entries
                lines[ind] = ''
    if not ovr:
        # make sure there is a newline
        if lines and not lines[-1].endswith(('\n', '\r')):
            lines[-1] = '{0}\n'.format(lines[-1])
        line = ip + '\t\t' + alias + '\n'
        lines.append(line)
    with salt.utils.fopen(hfn, 'w+') as ofile:
        ofile.writelines(lines)
    return True


def rm_host(ip, alias):
    '''
    Remove a host entry from the hosts file

    CLI Example::

        salt '*' hosts.rm_host <ip> <alias>
    '''
    if not has_pair(ip, alias):
        return True
    hfn = __get_hosts_filename()
    lines = salt.utils.fopen(hfn).readlines()
    for ind in range(len(lines)):
        tmpline = lines[ind].strip()
        if not tmpline:
            continue
        if tmpline.startswith('#'):
            continue
        comps = tmpline.split()
        if comps[0] == ip:
            newline = '{0}\t'.format(comps[0])
            for existing in comps[1:]:
                if existing == alias:
                    continue
                newline += '\t{0}'.format(existing)
            if newline.strip() == ip:
                # No aliases exist for the line, make it empty
                lines[ind] = ''
            else:
                # Only an alias was removed
                lines[ind] = '{0}\n'.format(newline)
    with salt.utils.fopen(hfn, 'w+') as ofile:
        ofile.writelines(lines)
    return True


def add_host(ip, alias):
    '''
    Add a host to an existing entry, if the entry is not in place then create
    it with the given host

    CLI Example::

        salt '*' hosts.add_host <ip> <alias>
    '''
    hfn = __get_hosts_filename()
    if not os.path.isfile(hfn):
        return False

    if has_pair(ip, alias):
        return True

    hosts = _list_hosts()
    hosts.setdefault(ip, []).append(alias)
    _write_hosts(hosts)
    return True


def _write_hosts(hosts):
    lines = []
    for ip, aliases in hosts.iteritems():
        lines.append(
            '{0}\t\t{1}'.format(ip, '\t'.join(aliases))
        )

    hfn = __get_hosts_filename()
    with salt.utils.fopen(hfn, 'w+') as ofile:
        ofile.write(
            '\n'.join(
                [l.strip() for l in lines if l.strip()]
            )
        )
