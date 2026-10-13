"""Build the complete Android GUARD-07 bundle with the existing installation's signer.

This builds and audits files only. It never installs an APK or starts a glasses OTA.
Passwords are passed to signing tools through environment variables.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
STOCK_SHA = '770ba0793d31609aa1e4477db2f8a7aec2c8acc4d9c6ab43d57b0dfc720d3ab3'
FIRMWARE_SHA = '5ef21d8c18501d03fad6edee4fe039649cb567352e30dbd234081ecf97140afa'
AP_SHA = '65e0a5312361ec785eb9ab1659badf182765f4054d4d95fef4c61ceb49dfa4b4'
PATCHED_LIB_SHA = '851e0c59babc656e4eb4f47e00f3947605c3ddba530eeef4b65e7942e2898541'
MARKER = 'assets/turboio/official-ota-guarded.txt'


def digest(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def require(condition, reason):
    if not condition:
        raise SystemExit(reason)


def main():
    require(sys.flags.optimize == 0, 'Run without Python optimization so upstream audits remain enabled.')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stock-apk', required=True, type=Path)
    parser.add_argument('--firmware', required=True, type=Path)
    parser.add_argument('--previous-apk', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    stock, firmware, previous, output = (p.resolve() for p in
        (args.stock_apk, args.firmware, args.previous_apk, args.output))
    require(not output.exists(), 'Output already exists; choose a new bundle directory.')
    sdk = Path(os.environ['ANDROID_SDK_ROOT']).resolve()
    tools = sdk / 'build-tools/36.0.0'
    keystore = Path(os.environ.get('ANDROID_DEBUG_KEYSTORE', str(Path.home() / '.android/debug.keystore')))
    env = os.environ.copy()
    env.pop('PYTHONOPTIMIZE', None)
    env.setdefault('TURBOIO_STORE_PASSWORD', 'android')
    env.setdefault('TURBOIO_KEY_PASSWORD', env['TURBOIO_STORE_PASSWORD'])
    alias = env.get('TURBOIO_KEY_ALIAS', 'androiddebugkey')
    env['TURBO_SDK_PYTHON'] = sys.executable
    env['PATH'] = str(Path(sys.executable).parent) + os.pathsep + env['PATH']
    require(digest(stock) == STOCK_SHA, 'Unsupported stock APK; no package modifications performed.')
    require(digest(firmware) == FIRMWARE_SHA, 'Wrong TAP1-TEST-01 ZIP; no package modifications performed.')
    with zipfile.ZipFile(firmware) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist())) == 15 and archive.testzip() is None,
                'Firmware ZIP integrity failed.')
        manifest = json.loads(archive.read('OtaFileInfo.json'))
        require(len(manifest) == 14, 'Firmware manifest member count differs.')
        for member in manifest:
            payload = archive.read(member['Name'])
            require(len(payload) == member['Size'] and hashlib.md5(payload).hexdigest() == member['Md5'],
                    'Firmware payload size/MD5 differs: ' + member['Name'])
        require(hashlib.sha256(archive.read('nuttx_ap.bin')).hexdigest() == AP_SHA, 'Wrong AP payload.')
    (ROOT / 'android-addon/build').mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='personal-guard07-', dir=ROOT / 'android-addon/build'))
    log = stage / 'build.log'

    def run(*command):
        with log.open('a') as handle:
            result = subprocess.run([str(x) for x in command], cwd=ROOT, env=env,
                                    stdout=handle, stderr=subprocess.STDOUT)
        require(result.returncode == 0, f'Command failed: {command[0]}; see {log}')

    def identity(apk):
        cert = subprocess.check_output([str(tools / 'apksigner'), 'verify', '--print-certs', str(apk)], text=True)
        fingerprint = re.search(r'Signer #1 certificate SHA-256 digest: ([a-f0-9]+)', cert)
        require(fingerprint is not None and 'Signer #2' not in cert, 'Expected one verified APK signer.')
        badging = subprocess.check_output([str(tools / 'aapt2'), 'dump', 'badging', str(apk)], text=True)
        package = next(line for line in badging.splitlines() if line.startswith('package:'))
        return dict(package=re.search(r"name='([^']+)'", package).group(1),
                    versionCode=re.search(r"versionCode='([^']+)'", package).group(1),
                    versionName=re.search(r"versionName='([^']+)'", package).group(1),
                    label=next(line for line in badging.splitlines() if line.startswith('application-label:')),
                    certificateSHA256=fingerprint.group(1))

    before = identity(previous)
    require(before['package'] == 'com.rayneo.venus.pub' and before['versionCode'] == '201',
            'Previous APK is not the expected 1.0.5 installation baseline.')
    certificate = subprocess.check_output(['keytool', '-exportcert', '-keystore', str(keystore),
        '-alias', alias, '-storepass:env', 'TURBOIO_STORE_PASSWORD'], env=env)
    require(hashlib.sha256(certificate).hexdigest() == before['certificateSHA256'],
            'Signing key differs from the previous APK. Refusing a non-covering installation package.')
    candidate = ROOT / 'official-addon/build/app-ap-20260927-test-01/StrixOS-1.0.4.12-TAP1-TEST-01-CANDIDATE-NOT-APPROVED.zip'
    candidate.parent.mkdir(parents=True, exist_ok=True)
    if firmware != candidate.resolve():
        shutil.copyfile(firmware, candidate)
    print('Input firmware and previous APK signer verified; running upstream build checks.', flush=True)
    run('bash', 'android-addon/build.sh')
    print('Build checks passed; packaging the complete GUARD-07 variant.', flush=True)
    run('node', 'android-addon/package.mjs', stock)
    run('node', 'android-addon/official-ota-source.mjs',
        ROOT / 'android-addon/build/host-105/lib/arm64-v8a/libapp.so', stage / 'route')
    guarded = stage / 'guarded-unsigned.apk'
    run(sys.executable, 'android-addon/package-official-ota-preparation.py', '--guarded', stock,
        ROOT / 'android-addon/build/TurboIO-RayNeo-1.0.5-unsigned.apk', stage / 'route/libapp.so', guarded)
    aligned = stage / 'guarded-aligned.apk'
    signed = stage / 'TurboIO-RayNeo-1.0.5_201-GUARD07-personal.apk'
    run(tools / 'zipalign', '-f', '-P', '16', '4', guarded, aligned)
    run(tools / 'apksigner', 'sign', '--ks', keystore, '--ks-key-alias', alias,
        '--ks-pass', 'env:TURBOIO_STORE_PASSWORD', '--key-pass', 'env:TURBOIO_KEY_PASSWORD', '--out', signed, aligned)
    run(tools / 'apksigner', 'verify', '--verbose', signed)
    run(tools / 'zipalign', '-c', '-P', '16', '4', signed)
    run(sys.executable, 'android-addon/tests/PrivateArtifactAudit.py', signed)
    after = identity(signed)
    require(before == after, 'Final APK package, version, name or signing certificate differs from the baseline.')
    with zipfile.ZipFile(guarded) as original, zipfile.ZipFile(signed) as final:
        require(final.testzip() is None, 'Final APK ZIP integrity failed.')
        require(len(final.namelist()) == len(set(final.namelist())), 'Duplicate final APK entries.')
        require(set(original.namelist()) <= set(final.namelist()), 'Signing removed APK payloads.')
        require(all(name.startswith('META-INF/') for name in set(final.namelist()) - set(original.namelist())),
                'Unexpected signing payload additions.')
        require(all(original.read(name) == final.read(name) for name in original.namelist()), 'Signed payload mismatch.')
        require(final.read(MARKER) == b'ANDROID-105-OFFICIAL-OTA-GUARD-02\n', 'GUARD-07 marker missing.')
        require('assets/turboio/official-ota-preparation.txt' not in final.namelist(), 'Wrong preparation-only variant.')
        require(hashlib.sha256(final.read('lib/arm64-v8a/libapp.so')).hexdigest() == PATCHED_LIB_SHA,
                'Official OTA source routing mismatch.')
    output.mkdir(parents=True)
    shutil.copyfile(signed, output / signed.name)
    shutil.copyfile(firmware, output / 'TurboIO-TAP1-TEST-01.zip')
    shutil.copyfile(ROOT / 'docs/ANDROID_PERSONAL_RELEASE.md', output / 'INSTALL.md')
    shutil.copyfile(log, output / 'build.log')
    shutil.copyfile(guarded.with_suffix('.audit.json'), output / 'guarded-package-audit.json')
    report = dict(profile='GUARD-07 / TAP1-TEST-01', sourceCommit=subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), previousAPK=str(previous),
        previousIdentity=before, outputIdentity=after, samePackageVersionNameAndSigner=True,
        apkSHA256=digest(signed), firmwareSHA256=FIRMWARE_SHA, firmwareAPSHA256=AP_SHA,
        upstreamBuildChecksPassed=True, privateArtifactAuditPassed=True, signedPayloadsPreserved=True,
        zipalign16KiBPassed=True, fixedOfficialOTAEnabled=True, defaultUpgradeAuthorization=0,
        installed=False, firmwareFlashed=False, bindingPreservationDeviceValidated=False)
    (output / 'build-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    (output / 'SHA256SUMS.txt').write_text(''.join(
        digest(path) + '  ' + path.name + '\n' for path in sorted(output.iterdir()) if path.is_file()))
    print(f'Complete audited bundle: {output}', flush=True)


if __name__ == '__main__':
    main()
