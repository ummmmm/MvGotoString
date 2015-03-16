import sublime, sublime_plugin
import os.path
import re
import threading

class MvGotoString( sublime_plugin.WindowCommand ):
	def run( self ):
		self.current_view 	= self.window.active_view()
		self.settings		= sublime.load_settings( 'mv_goto_string.sublime-settings' )

		if type( self.settings.get( 'file_types' ) ) is not list:
			sublime.status_message( 'Invalid file types value' )
			return

		self.window.show_input_panel( 'Search {0} files for string:' . format( '/' . join( self.settings.get( 'file_types' ) ) ), '', self.on_done, None, None )

	def on_done( self, value ):
		thread = SearchFilesThread( value, self.settings, on_complete = self.results_quick_panel )
		thread.start()
		ThreadProgress( thread, 'Searching {0} files for string {1}' . format( '/' . join( self.settings.get( 'file_types' ) ),value ) )

	def results_quick_panel( self, results, selected_index = -1 ):
		sublime.set_timeout( lambda: self.window.show_quick_panel( [ self.format_entry( result ) for result in results ], lambda index: self.select_entry( results, index ), selected_index = selected_index, on_highlight = lambda index: self.highlight_entry( results, index ) ), 10 )

	def goto_file( self, file_path, row, col, args ):
		self.window.open_file( '{0}:{1}:{2}' . format( file_path, row, col ), args )

	def select_entry( self, results, index ):
		if index == -1:
			if self.current_view:
				self.window.focus_view( self.current_view )

			return

		result = results[ index ]

		self.goto_file( result[ 'mv_file' ][ 'file_path' ], result[ 'lineno' ], result[ 'col' ], sublime.ENCODED_POSITION )
		self.results_quick_panel( results, selected_index = index )

	def format_entry( self, result ):
		return [ '{0}:{1}' . format( result[ 'mv_file' ][ 'file_name' ], result[ 'lineno' ] ), result[ 'preview' ], result[ 'mv_file' ][ 'file_path' ] ]

	def highlight_entry( self, results, index ):
		result = results[ index ]

		self.goto_file( result[ 'mv_file' ][ 'file_path' ], result[ 'lineno' ], result[ 'col' ], sublime.ENCODED_POSITION | sublime.TRANSIENT )

#
# Threading Classes
#

class ThreadProgress():
	def __init__( self, thread, message, success_message = '' ):
		self.thread 			= thread
		self.message 			= message
		self.success_message 	= success_message
		self.addend 			= 1
		self.size 				= 8

		sublime.set_timeout( lambda: self.run( 0 ), 100 )

	def run( self, i ):
		if not self.thread.is_alive():
			if hasattr( self.thread, 'result' ) and not self.thread.result:
				return sublime.status_message('')

			return sublime.status_message( self.success_message )

		before 	= i % self.size
		after 	= ( self.size - 1 ) - before

		sublime.status_message( '{0} [{1}={2}]' . format( self.message, ' ' * before, ' ' * after ) )

		if not after:
			self.addend = -1

		if not before:
			self.addend = 1

		i += self.addend

		sublime.set_timeout( lambda: self.run( i ), 100 )

class SearchFilesThread( threading.Thread ):
	def __init__( self, value, settings, on_complete ):
		self.value			= value
		self.settings 		= settings
		self.on_complete	= on_complete
		threading.Thread.__init__( self )

	def run( self ):
		results = []

		if not self.settings.get( 'case_sensitive', True ):
			regex_flag	= re.IGNORECASE
		else:
			regex_flag	= 0

		regex_search	= re.compile( "{string}" . format( string = re.escape( self.value ) ), regex_flag )

		for mv_file in self.get_valid_files():
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

		sublime.set_timeout( lambda: self.on_complete( results ), 10 )

	def get_valid_files( self ):
		files 		= []
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
						files.append( { 'file_path': os.path.join( root, file ), 'file_name': file } )

		return files
