#  Phalcon Framework
#
#  Copyright (c) 2011-2016, Phalcon Team (https://www.phalconphp.com)
#
#  This source file is subject to the New BSD License that is bundled
#  with this package in the file https://www.phalconphp.com/LICENSE.txt
#
#  If you did not receive a copy of the license and are unable to
#  obtain it through the world-wide-web, please send an email
#  to license@phalconphp.com so we can send you a copy immediately.
#
#  Authors: Andres Gutierrez <andres@phalconphp.com>
#           Serghei Iakovlev <serghei@phalconphp.com>

%global with_zts    0%{?__ztsphp:1}
%global with_tests  %{?_with_tests:1}%{!?_with_tests:0}
%global ext_name    phalcon
%global php_apiver  %((rpm -E %php_core_api | cut -d '-' -f 1) | tail -1)
%global zend_apiver %((rpm -E %php_zend_api | cut -d '-' -f 1) | tail -1)
%global php_major   %((rpm -E %php_version  | cut -d. -f1)     | tail -1)
# will be replaced by the automated script
%global php_base    php56u
# will be replaced by the automated script
%global repo_vendor ius
# after 40-json.ini, 20-pdo.ini
%global ini_name    50-%{ext_name}.ini

%global src_dir cphalcon/build/php%{php_major}/safe
%if %{__isa_bits} == 32
%global src_dir cphalcon/build/php%{php_major}/32bits
%endif
%if %{__isa_bits} == 64
%global src_dir cphalcon/build/php%{php_major}/64bits
%endif

%if 0%{?fedora} >= 17 || 0%{?rhel} >= 7
%global with_libpcre  1
%else
%global with_libpcre  0
%endif

Name: %{php_base}-phalcon
Version: %{version}
# will be replaced by the automated script
Release: 1.%{repo_vendor}%{?dist}
Summary: High performance PHP framework
Group: Development/Libraries
Packager: Phalcon Buildbot <build@phalconphp.com>
License: BSD 3-Clause
URL: https://github.com/phalcon/cphalcon
Source0: phalcon-php-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
%if %{php_major} == 5
BuildRequires: %{php_base}-pecl-jsonc-devel%{?_isa}
%endif
BuildRequires: %{php_base}-devel%{?_isa}
%if %{with_libpcre}
BuildRequires: pcre-devel%{?_isa} >= 8.20
%endif
BuildRequires: re2c%{?_isa}
Requires: %{php_base}-pdo%{?_isa}
Requires: %{php_base}-common%{?_isa}
Requires: %{php_base}(zend-abi) = %{zend_apiver}
Requires: %{php_base}(api) = %{php_apiver}

%description
High performance PHP framework.

Phalcon is an open source web framework delivered as a C extension for
the PHP language providing high performance and lower resource consumption.

This package provides the Phalcon PHP extension.

Documentation: https://docs.phalconphp.com

%prep
%setup -q -n phalcon-php-%{version}

%{__cat} > %{ini_name} << 'EOF'
;
;  Phalcon Framework
;
;  Copyright (c) 2011-2016 Phalcon Team (https://www.phalconphp.com)
;
;  This source file is subject to the New BSD License that is bundled
;  with this package in the file https://www.phalconphp.com/LICENSE.txt
;
;  If you did not receive a copy of the license and are unable to
;  obtain it through the world-wide-web, please send an email
;  to license@phalconphp.com so we can send you a copy immediately.
;
;  Authors: Andres Gutierrez <andres@phalconphp.com>
;           Serghei Iakovlev <serghei@phalconphp.com>

; %{summary}
[%{ext_name}]
extension = %{ext_name}.so

; ----- Options to use the Phalcon Framework

; %{ext_name}.db.escape_identifiers = On
; %{ext_name}.db.force_casting = Off

; %{ext_name}.orm.events = On
; %{ext_name}.orm.virtual_foreign_keys = On
; %{ext_name}.orm.column_renaming = On
; %{ext_name}.orm.not_null_validations = On
; %{ext_name}.orm.exception_on_failed_save = Off
; %{ext_name}.orm.enable_literals = On
; %{ext_name}.orm.late_state_binding = Off
; %{ext_name}.orm.enable_implicit_joins = On
; %{ext_name}.orm.cast_on_hydrate = Off
; %{ext_name}.orm.ignore_unknown_columns = Off

EOF

%build
extconf() {
%configure \
  --enable-phalcon \
  --with-libdir=%{_lib} \
  --with-php-config=$1
}

: Generate the SAFE sources

CFLAGS+="-O2 -fvisibility=hidden -finline-functions"
LDFLAGS+="-Wl,--as-needed -Wl,-Bsymbolic-functions"

export CC="gcc"
export LDFLAGS
export CFLAGS
export CPPFLAGS="-DPHALCON_RELEASE"

%{__mv} %{src_dir} build/NTS

%if %{with_zts}
: Duplicate source tree for NTS / ZTS build
%{__cp} -r build/NTS build/ZTS
%endif

: Build NTS extension
cd build/NTS
%{_bindir}/phpize
extconf %{_bindir}/php-config
%{__make} %{?_smp_mflags}

%if %{with_zts}
: Build ZTS extension
cd ../ZTS
%{_bindir}/zts-phpize
extconf %{_bindir}/zts-php-config
%{__make} %{?_smp_mflags}
%endif

%install
%{__rm} -rf ${buildroot}
%{__make} -C build/NTS install INSTALL_ROOT=%{buildroot}
%{__install} -D -m 644 %{ini_name} %{buildroot}%{php_inidir}/%{ini_name}

%if %{with_zts}
%{__make} -C build/ZTS install INSTALL_ROOT=%{buildroot}
%{__install} -Dpm644 %{ini_name} %{buildroot}%{php_ztsinidir}/%{ini_name}
%endif

%check
: Get needed extensions for check
modules=""
for mod in json pdo; do
  if [ -f %{php_extdir}/${mod}.so ]; then
    modules="$modules -d extension=${mod}.so"
  fi
done

: Minimal load test for NTS extension
%{__php} --no-php-ini \
    $modules \
    --define extension=%{buildroot}%{php_extdir}/%{ext_name}.so \
    --modules | grep -i %{ext_name}

%if %{with_tests}
: Upstream test suite NTS extension
cd build/NTS
SKIP_ONLINE_TESTS=1 \
TEST_PHP_EXECUTABLE=%{__php} \
TEST_PHP_ARGS="-n $modules -d extension=$PWD/modules/%{ext_name}.so" \
NO_INTERACTION=1 \
REPORT_EXIT_STATUS=1 \
%{__php} -n run-tests.php --show-diff
%endif

%if %{with_zts}
: Minimal load test for ZTS extension
%{__ztsphp} --no-php-ini \
    $modules \
    --define extension=%{buildroot}%{php_ztsextdir}/%{ext_name}.so \
    --modules | grep -i %{ext_name}
%endif

%clean
extclean() {
[ -f Makefile ] && %{__make} distclean; \
    %{_bindir}/$1 --clean; \
    %{__rm} -f tmp-php.ini
}

cd build/NTS
extclean phpize

%if %{with_zts}
cd ../ZTS
extclean zts-phpize
%endif

%{__rm} -rf ${buildroot}

%files
%defattr(-,root,root,-)
%{!?_licensedir:%global license %%doc}
%license cphalcon/docs/LICENSE.txt
%doc cphalcon/CHANGELOG.md
%doc cphalcon/CONTRIBUTING.md
%doc cphalcon/README.md

%{php_extdir}/%{ext_name}.so
%config(noreplace) %{php_inidir}/%{ini_name}
%{php_incldir}/ext/%{ext_name}/php_phalcon.h

%if %{with_zts}
%{php_ztsextdir}/%{ext_name}.so
%config(noreplace) %{php_ztsinidir}/%{ini_name}
%{php_ztsincldir}/ext/%{ext_name}/php_phalcon.h
%endif

%changelog
 * Wed Aug 24 2016 Serghei Iakovlev <serghei@phalconphp.com> - %{version}-%{release}.%{repo_vendor}
- Fixed Phalcon\Cache\Backend\Redis::flush in order to flush cache correctly
- Fixed Phalcon\Mvc\Model\Manager::getRelationRecords to correct using multi relation column #12035
- Fixed Phalcon\Acl\Resource. Now it implements Phalcon\Acl\ResourceInterface #11959
- Fixed save method for all cache backends. Now it updates the _lastKey property correctly #12050
- Fixed virtual foreign key check when having multiple keys #12071
- Phalcon\Config\Adapter\Ini constructor can now specify parse_ini_file() scanner mode #12079
- Fixed Phalcon\Cache\Backend\Apc::save due to which the Apc::increment/Apc::decrement could not be used properly #12109
- Fixed Phalcon\Mvc\Model\Criteria::inWhere so that now the second parameter can be an empty array #10676
- Fixed ORM related memory leak #12115, #11995, #12116
- Fixed incorrect Phalcon\Mvc\View::getActiveRenderPath behavior #12139
- Fixed Phalcon\Security\Random::base64Safe so that now the method returns correct safe string #12141
- Fixed the Phalcon\Translate\Adapter\Gettext::getOptionsDefault visibility #12157
- Enabled PHQL cache for PHP7 to improve performance and reuse plannings

* Thu Aug 18 2016 Serghei Iakovlev <serghei@phalconphp.com> - 3.0.0-29.%{repo_vendor}
- Initial Packagecloud release
