%global debug_package %{nil}
%{?!released_version: %global released_version 0.1.2}

# ---------------
# task-core
# ---------------

Name:           task-core
Summary:        task-core
Version:        %{released_version}
Release:        1%{?dist}

License:        ASL 2.0

URL:            https://github.com/Directord/task-core
Source:         https://github.com/Directord/task-core/archive/%{version}.tar.gz#/task-core-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python3-pbr >= 2.0.0

Recommends:     python3-%{name}
Recommends:     %{name}-examples

%description
task-core

# ---------------
# Python package
# ---------------

%package -n python3-%{name}
Summary:        Python library code for task-core

Requires:       %{name} = %{version}-%{release}
# python requirements
Requires:       python3-jsonschema
Requires:       python3-networkx
Requires:       python3-stevedore
Requires:       python3-taskflow
Requires:       python3-yaml
# these are backends
Recommends:     directord
Recommends:     python3-ansible-runner

%{?python_provide:%python_provide python3-%{name}}

%description -n python3-%{name}
Python library code for task-core

# ---------------
# Example package
# ---------------

%package -n %{name}-examples
Summary:        Example service and tasks for task-core

Requires:       %{name} = %{version}-%{release}

%description -n %{name}-examples
Example service and tasks for task-core

# ---------------
# Setup
# ---------------

%prep
%autosetup -n task-core-%{version} -S git
rm -rf *.egg-info

# ---------------
# Build
# ---------------

%build
%{py3_build}

# ---------------
#  Install
# ---------------

%install
%{py3_install}

# ---------------
#  Misc
# ---------------

%check
# TODO(mwhahaha): run tests

%post

%preun

# ---------------
# Files
# ---------------

%files
%license LICENSE
%doc README.rst AUTHORS ChangeLog
%{_datadir}/%{name}
%exclude %{_datadir}/%{name}/examples
%exclude %{_datadir}/%{name}/schema

%files -n python3-%{name}
%license LICENSE
%doc README.rst AUTHORS ChangeLog
%{python3_sitelib}/task_core*
%{_bindir}/%{name}
%{_bindir}/task-core-example
%{_datadir}/%{name}/schema
%{_datadir}/%{name}/contrib

%files -n %{name}-examples
%license LICENSE
%doc README.rst AUTHORS ChangeLog
%{_datadir}/%{name}/examples

# ---------------

%changelog
* Mon Oct 25 2021 Alex Schultz <aschultz@redhat.com> - 0.1.2-1
- Fixes tag for release rpms

* Mon Oct 25 2021 Alex Schultz <aschultz@redhat.com> - 0.1.1-1
- Fixes repository move

* Mon Oct 25 2021 Alex Schultz <aschultz@redhat.com> - 0.1.0-1
- Initial 0.1.0 release

* Thu Jul 29 2021 Alex Schultz <aschultz@redhat.com> - 0.0.1-1
- Initial Release
