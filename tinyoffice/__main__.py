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
    default=['.docx', '.pptx', '.xlsx'],
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
    help='Flag for disabling optimization passes on JPEGs and PNGS',
)
args = parser.parse_args()

image_extensions = args.extensions if args.extensions else None
types = args.types if args.types else None

if args.verbose <= 0:
    verbosity = tinyoffice.Verbosity.NONE
elif args.verbose == 1:
    verbosity = tinyoffice.Verbosity.LOW
elif args.verbose == 2:
    verbosity = tinyoffice.Verbosity.NORMAL
else:
    verbosity = tinyoffice.Verbosity.HIGH

path = os.path.realpath(args.path)
output = os.path.realpath(args.output) if args.output else args.output

if args.recurse:
    tinyoffice.walk(
        path,
        types=types,
        overwrite=args.overwrite,
        output=output,
        convert=args.convert,
        verbosity=verbosity,
        image_extensions=image_extensions,
        jpeg_quality=args.jpeg_quality,
        tiff_quality=args.tiff_quality,
        optimize=not args.no_optimize,
    )
else:
    if os.path.isdir(path):
        tinyoffice.listdir(
            path,
            types=types,
            overwrite=args.overwrite,
            output=output,
            convert=args.convert,
            verbosity=verbosity,
            image_extensions=image_extensions,
            jpeg_quality=args.jpeg_quality,
            tiff_quality=args.tiff_quality,
            optimize=not args.no_optimize,
        )
    else:
        if output is None or not os.path.splitext(output)[1]:
            output = os.path.join(output, os.path.split(path)[1])
        if args.overwrite or not os.path.isfile(path):
            result = tinyoffice.process(
                path,
                output=output,
                convert=args.convert,
                image_extensions=image_extensions,
                jpeg_quality=args.jpeg_quality,
                tiff_quality=args.tiff_quality,
                optimize=not args.no_optimize,
            )
            if verbosity is tinyoffice.Verbosity.LOW:
                if result.num_images_compressed:
                    print(
                        f'Compressed {result.filename}. '
                        f'{len(result.errors):,} Error(s) encountered.'
                    )
            elif verbosity is tinyoffice.Verbosity.NORMAL:
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
            elif verbosity is tinyoffice.Verbosity.HIGH:
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
