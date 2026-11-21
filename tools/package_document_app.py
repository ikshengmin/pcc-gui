"""Package an application resource directory using the platform's PCC-GUI document host."""
import argparse
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile


def package_darwin(resources, config, output, reuse):
    executable = config['executable']
    if not executable or Path(executable).name != executable or executable in ('.', '..'):
        raise ValueError('Expected one executable filename')
    with tempfile.TemporaryDirectory(dir=output.parent) as stage:
        bundle = Path(stage) / output.name
        target = bundle / 'Contents/MacOS' / executable
        target.parent.mkdir(parents=True)
        shutil.copytree(resources, bundle / 'Contents/Resources')
        if reuse:
            info = plistlib.loads((reuse / 'Contents/Info.plist').read_bytes())
            if info.get('PCCDocumentProtocol') != 2:
                # Earlier v2 hosts recorded their input protocol in this resource.
                receipt = reuse / 'Contents/Resources/direct-preview.json'
                if not receipt.is_file() or json.loads(receipt.read_bytes()).get('input_protocol') != 2:
                    raise ValueError('The selected host must support document input protocol v2')
            shutil.copy2(reuse / 'Contents/MacOS' / info['CFBundleExecutable'], target)
        else:
            native = Path(__file__).resolve().parents[1] / 'pcc_gui/native'
            sdk = subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
            frameworks = [flag for name in ('AppKit','CoreGraphics','CoreText','Metal','QuartzCore')
                          for flag in ('-framework',name)]
            subprocess.run(['xcrun','--sdk','macosx','clang','-fobjc-arc','-fblocks','-O1',
                            '-Wno-deprecated-declarations','-isysroot',sdk,'-I',str(native),
                            str(native/'pcc_gui_document_host_darwin.m'),
                            str(native/'pcc_gui_metal_render_bridge.m'),*frameworks,'-o',str(target)],check=True)
        info = dict(CFBundleName=config['name'], CFBundleDisplayName=config['name'],
                    CFBundleIdentifier=config['identifier'], CFBundlePackageType='APPL',
                    CFBundleExecutable=executable, CFBundleVersion='1', CFBundleShortVersionString='0.1',
                    NSHighResolutionCapable=True, NSRequiresAquaSystemAppearance=True,
                    PCCDocumentProtocol=2, TAGDocumentButtons=config.get('buttons',[]))
        for key, setting in [('password_input','TAGDocumentPasswordInput'),('status','PCCDocumentStatus'),
                             ('opening_label','PCCDocumentOpeningLabel')]:
            if key in config:
                info[setting]=config[key]
        (bundle/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
        subprocess.run(['codesign','--force','--deep','--sign','-',str(bundle)],check=True)
        subprocess.run(['codesign','--verify','--strict','--deep',str(bundle)],check=True)
        bundle.rename(output)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resources',type=Path,required=True)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--reuse-host',type=Path)
    args=parser.parse_args()
    output=args.out.absolute()
    if output.exists():
        raise FileExistsError(output)
    if sys.platform!='darwin':
        parser.exit(2, f'PCC-GUI has no native document window provider for {sys.platform} yet. The renderer can run independently.\n')
    output.parent.mkdir(parents=True,exist_ok=True)
    package_darwin(args.resources,json.loads(args.config.read_bytes()),output,args.reuse_host)


if __name__=='__main__':
    main()
