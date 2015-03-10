import sublime, sublime_plugin
import os.path
import re

class MvGotoString( sublime_plugin.WindowCommand ):
	def run( self ):
		self.current_view 	= self.window.active_view()
		self.settings		= sublime.load_settings( 'mv_goto_string.sublime-settings' )

		if type( self.settings.get( 'file_types' ) ) is not list:
			sublime.status_message( 'Invalid file types value' )
			print( 'File types setting must be an array' )
			return

		self.window.show_input_panel( 'Search {0} files for string:' . format( '/' . join( self.settings.get( 'file_types' ) ) ), '', self.on_done, None, None )

	def on_done( self, value ):
		results 		= []

		if not self.settings.get( 'case_sensitive', True ):
			regex_flag	= re.IGNORECASE
		else:
			regex_flag	= 0

		regex_search	= re.compile( "{string}" . format( string = re.escape( value ) ), regex_flag )

		for mv_file in self.get_mv_files():
			lineno = 0

			try:
				with open( mv_file[ 'file_path' ], 'r' ) as fh:
					for line in fh:
						lineno += 1
						result	= regex_search.search( line )

						if not result:
							continue

						line_length				= len( line )
						span_start, span_stop 	= result.span()

						if span_start - 10 < 0:
							start = 0
						else:
							start = span_start - 10

						if span_stop + 10 > line_length:
							stop = span_stop + ( line_length - span_stop )
						else:
							stop = span_stop + 10

						results.append( { 'mv_file': mv_file, 'lineno': lineno, 'preview': line[ start : stop ].strip(), 'col': span_start + 1 } )

			except UnicodeDecodeError:
				print( 'Failed to read {0} do a utf-8 issue' . format ( mv_file[ 'file_path' ] ) )
				continue

		if len( results ) == 0:
			sublime.status_message( 'Failed to find string \'{0}\'' . format( value ) )
			return

		self.window.show_quick_panel( [ self.format_entry( result ) for result in results ], lambda index: self.select_entry( results, index ), on_highlight = lambda index: self.highlight_entry( results, index ) )

	def get_mv_files( self ):
		mv_files 	= []
		paths 		= []
		path		= self.settings.get( 'path' )
		path_type	= type( self.settings.get( 'path' ) )

		if path_type is str:
			paths.append( path )
		elif path_type is list:
			paths = path
		else:
			sublime.status_message( 'Invalid value for path' )

		for path in paths:
			if not os.path.isdir( path ):
				print( "Invalid directory path '{0}'" . format( path ) )
				continue

			for root, dirs, filenames in os.walk( path ):
				for file in filenames:
					if file.endswith( tuple( self.settings.get( 'file_types' ) ) ):
						mv_files.append( { 'file_path': os.path.join( root, file ), 'file_name': file } )

		return mv_files

	def goto_file( self, file_path, row, col, args ):
		self.window.open_file( '{0}:{1}:{2}' . format( file_path, row, col ), args )

	def select_entry( self, results, index ):
		if index == -1:
			if self.current_view:
				self.window.focus_view( self.current_view )	

			return

		result = results[ index ]

		self.goto_file( result[ 'mv_file' ][ 'file_path' ], result[ 'lineno' ], result[ 'col' ], sublime.ENCODED_POSITION )

	def format_entry( self, result ):
		return [ '{0}:{1}' . format( result[ 'mv_file' ][ 'file_name' ], result[ 'lineno' ] ), result[ 'preview' ], result[ 'mv_file' ][ 'file_path' ] ]

	def highlight_entry( self, results, index ):
		result = results[ index ]

		self.goto_file( result[ 'mv_file' ][ 'file_path' ], result[ 'lineno' ], result[ 'col' ], sublime.ENCODED_POSITION | sublime.TRANSIENT )
