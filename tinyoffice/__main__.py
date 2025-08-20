import argparse
import os

from . import tinyoffice

parser = argparse.ArgumentParser(
    prog='tinyoffice',
    allow_abbrev=False,
    formatter_class=argparse.RawTextHelpFormatter,
    description='Make your Office files tiny!',
)
parser.add_argument(
    'path',
    type=os.path.realpath,
    help='File or directory path.\nIf a file and recurse (-r/--recurse) '
         'is not set, only that file will be compressed.\nIf a directory, '
         'and recurse is not set, only the top-level files in the '
         'directory will be compressed.\nIf recurse is set, everything '
         'at path and below will be compressed.'
)
parser.add_argument(
    '-r',
    '--recurse',
    action='store_true',
    default=False,
    help='Flag for if tinyoffice should recursively search for files. '
         'Default is False',
)
parser.add_argument(
    '-c',
    '--convert',
    action='store_true',
    default=False,
    help='Flag for if TIFF files should be converted to JPEGs. '
         'Default is False',
)
parser.add_argument(
    '-v',
    '--verbose',
    action='count',
    default=0,
    help='Flag for verbosity levels. Can be set multiple times, e.g., -vv, '
         'for increased verbosity',
)
parser.add_argument(
    '-t',
    '--types',
    nargs='+',
    choices=['.docx', '.pptx', '.xlsx'],
    default={'.docx', '.pptx', '.xlsx'},
    metavar='.docx .pptx .xlsx',
    help='Filetype extensions to compress.\nDefault is .docx, .pptx, .xlsx',
)
parser.add_argument(
    '--overwrite',
    action='store_true',
    default=False,
    help='Flag for if an existing file should be overwritten. '
         'Default is False',
)
parser.add_argument(
    '-o',
    '--output',
    type=os.path.realpath,
    help='Path for the output location.',
)
parser.add_argument(
    '-exts',
    '--extensions',
    nargs='+',
    help='Image extensions to compress. Default will be only the extensions '
         'that are supported by Pillow on your system.\nShould be ignored.'
)
parser.add_argument(
    '--jpeg-quality',
    default=75,
    type=int,
    help='Default is 75',
)
parser.add_argument(
    '--tiff-quality',
    default=75,
    type=int,
    help='Default is 75',
)
parser.add_argument(
    '--no-optimize',
    default=False,
    action='store_true',
    help='Flag for disabling optimization passes on JPEGs and PNGS. '
         'Images are optimized by Default.',
)
args = parser.parse_args()

if args.verbose <= 0:
    args.verbose = tinyoffice.Verbosity.NONE
elif args.verbose == 1:
    args.verbose = tinyoffice.Verbosity.LOW
elif args.verbose == 2:
    args.verbose = tinyoffice.Verbosity.NORMAL
else:
    args.verbose = tinyoffice.Verbosity.HIGH

if args.recurse:
    tinyoffice.walk(
        args.path,
        types=args.types,
        overwrite=args.overwrite,
        output=args.output,
        convert=args.convert,
        verbosity=args.verbose,
        image_extensions=args.extensions,
        jpeg_quality=args.jpeg_quality,
        tiff_quality=args.tiff_quality,
        optimize=not args.no_optimize,
    )
else:
    if os.path.isdir(args.path):
        tinyoffice.listdir(
            args.path,
            types=args.types,
            overwrite=args.overwrite,
            output=args.output,
            convert=args.convert,
            verbosity=args.verbose,
            image_extensions=args.extensions,
            jpeg_quality=args.jpeg_quality,
            tiff_quality=args.tiff_quality,
            optimize=not args.no_optimize,
        )
    else:
        args.output = args.output if args.output else args.path
        if args.overwrite or not os.path.isfile(args.output):
            result = tinyoffice.process(
                args.path,
                output=args.output,
                convert=args.convert,
                image_extensions=args.extensions,
                jpeg_quality=args.jpeg_quality,
                tiff_quality=args.tiff_quality,
                optimize=not args.no_optimize,
            )
            if args.verbose is tinyoffice.Verbosity.LOW:
                if result.num_images_compressed:
                    print(
                        f'Compressed {result.filename}. '
                        f'{len(result.errors):,} Error(s) encountered.'
                    )
            elif args.verbose is tinyoffice.Verbosity.NORMAL:
                if result.num_images_compressed:
                    print(
                        f'Filename: {result.filename}.'
                        '\n'
                        f'Results: '
                        f'{result.num_images_compressed:,} compressed, '
                        f'{result.num_images_converted:,} converted, '
                        f'{result.num_images_skipped:,} skipped'
                        '\n'
                        f'Errors: {len(result.errors):,}'
                    )
                else:
                    print(
                        f'No compressed images for {result.filename}. '
                        f'{len(result.errors):,} Error(s) encountered.'
                    )
            elif args.verbose is tinyoffice.Verbosity.HIGH:
                print(
                    f'Filename: {result.filename}.'
                    '\n'
                    'Results: '
                    f'{result.num_images_compressed:,} compressed, '
                    f'{result.num_images_converted:,} converted, '
                    f'{result.num_images_skipped:,} skipped'
                    '\n'
                    'Errors:\n\t'
                    "\n".join(result.errors)
                )
