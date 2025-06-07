ARG EDITION VARIANT
FROM checkmk/check-mk-${EDITION}:${VARIANT}

RUN /docker-entrypoint.sh /bin/true

RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends nodejs gcc

#RUN 'curl https://www.arbiter.com/files/software/ntp_ptp/ARBITER-ALL-MIB.mib -o /omd/sites/cmk/local/share/snmp/mibs/ARBITER-ALL-MIB.mib'
ADD requirements.txt /tmp/requirements.txt
USER cmk
RUN PATH="/omd/sites/cmk/bin:${PATH}" \
    OMD_ROOT="/omd/sites/cmk" \
    /omd/sites/cmk/bin/pip3 install -r /tmp/requirements.txt

ENTRYPOINT ["/bin/bash"]
